import csv,io,time
from datetime import datetime,timezone,timedelta
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from src.models.identity import User
from src.models.run import Run
from src.models.delta import Delta,DeltaItem,GroupLedger
from src.services.audit import log
from src.utils.serialize import row
CN=timezone(timedelta(hours=8))
def stream_of(run): return run.snapshot.get('period','全部'),run.snapshot['policy']['version']
def stream_key(run):
 p,v=stream_of(run);return p+'|'+v
def group_of(r): return {'日期':r['日期'],'试制线':r['试制线'],'班次':r['班次']}
def group_key(r): return '|'.join((r['日期'],r['试制线'],r['班次']))
def generate(db):
 runs=db.query(Run).filter(Run.approved==True,Run.status=='completed').order_by(Run.id).all()
 recipients=db.query(User).order_by(User.id).all()
 done={x.due_key for x in db.query(Delta).all()}
 made=0
 for run in runs:
  if not run.result: continue
  period,version=stream_of(run);stream=stream_key(run)
  target={}
  for r in run.result.get('rows',[]): target[group_key(r)]=r
  for u in recipients:
   due='delta:%s:%s'%(u.email,run.id)
   if due in done: continue
   ledgers={x.group_key:x for x in db.query(GroupLedger).filter_by(recipient=u.email,stream=stream).all()}
   pendings={x.group_key for x in db.query(DeltaItem).filter_by(recipient=u.email,stream=stream,status='pending').all()}
   delta=Delta(recipient=u.email,period=period,policy_version=version,run_id=run.id,due_key=due,created=time.time())
   db.add(delta);db.flush()
   items=[]
   for key,r in sorted(target.items()):
    if key in pendings: continue
    led=ledgers.get(key)
    bn,bd,bl=(led.num_total,led.den_total,led.lot_total) if led else (0,0,0)
    dn,dd,dl=r['分子合计']-bn,r['分母合计']-bd,r['批数']-bl
    if not (dn or dd or dl): continue
    items.append(DeltaItem(delta_id=delta.id,recipient=u.email,stream=stream,group_key=key,group_info=group_of(r),base_run_id=led.confirmed_run_id if led else 0,target_run_id=run.id,num_delta=dn,den_delta=dd,lot_delta=dl,status='pending',pending_key=u.email+'|'+stream+'|'+key))
   for key,led in sorted(ledgers.items()):
    if key in target or key in pendings: continue
    if not (led.num_total or led.den_total or led.lot_total): continue
    items.append(DeltaItem(delta_id=delta.id,recipient=u.email,stream=stream,group_key=key,group_info=led.group_info,base_run_id=led.confirmed_run_id,target_run_id=run.id,num_delta=-led.num_total,den_delta=-led.den_total,lot_delta=-led.lot_total,status='pending',pending_key=u.email+'|'+stream+'|'+key))
   db.add_all(items);log(db,'worker','delta.generate','%s 净变动项 %d'%(due,len(items)))
   try: db.commit()
   except IntegrityError: db.rollback();continue
   done.add(due);made+=1
 return made
def catch_up(db,user,stream,gkey):
 runs=[r for r in db.query(Run).filter(Run.approved==True,Run.status=='completed').order_by(Run.id).all() if stream_key(r)==stream]
 if not runs: return None
 run=runs[-1]
 led=db.query(GroupLedger).filter_by(ledger_key=user.email+'|'+stream+'|'+gkey).first()
 if not led: return None
 if db.query(DeltaItem).filter_by(recipient=user.email,stream=stream,group_key=gkey,status='pending').first(): return None
 target={}
 for r in (run.result or {}).get('rows',[]): target[group_key(r)]=r
 r=target.get(gkey)
 gn,gd,gl=(r['分子合计'],r['分母合计'],r['批数']) if r else (0,0,0)
 dn,dd,dl=gn-led.num_total,gd-led.den_total,gl-led.lot_total
 if not (dn or dd or dl): return None
 due='delta:%s:%s:from:%s:%s'%(user.email,run.id,led.confirmed_run_id,gkey)
 if db.query(Delta).filter_by(due_key=due).first(): return None
 period,version=stream_of(run)
 delta=Delta(recipient=user.email,period=period,policy_version=version,run_id=run.id,due_key=due,created=time.time())
 db.add(delta);db.flush()
 db.add(DeltaItem(delta_id=delta.id,recipient=user.email,stream=stream,group_key=gkey,group_info=(r and group_of(r)) or led.group_info,base_run_id=led.confirmed_run_id,target_run_id=run.id,num_delta=dn,den_delta=dd,lot_delta=dl,status='pending',pending_key=user.email+'|'+stream+'|'+gkey))
 log(db,user.email,'delta.catchup','组 %s 追至报告 %s'%(gkey,run.id))
 try: db.commit()
 except IntegrityError: db.rollback();return None
 return delta
def confirm_item(db,user,item_id):
 item=db.query(DeltaItem).filter(DeltaItem.id==item_id).with_for_update().first()
 if not item or item.recipient!=user.email: raise HTTPException(404,'补差项不存在')
 if item.status=='confirmed':
  catch_up(db,user,item.stream,item.group_key)
  return item,False
 item.status='confirmed';item.confirmed_at=time.time();item.pending_key=None
 key=user.email+'|'+item.stream+'|'+item.group_key
 led=db.query(GroupLedger).filter_by(ledger_key=key).with_for_update().first()
 if not led:
  led=GroupLedger(ledger_key=key,recipient=user.email,stream=item.stream,group_key=item.group_key,group_info=item.group_info,confirmed_run_id=0,num_total=0,den_total=0,lot_total=0)
  db.add(led)
 led.num_total+=item.num_delta;led.den_total+=item.den_delta;led.lot_total+=item.lot_delta;led.confirmed_run_id=item.target_run_id
 log(db,user.email,'delta.confirm','补差项 %d → 报告 %s'%(item.id,item.target_run_id));db.commit()
 catch_up(db,user,item.stream,item.group_key)
 return item,True
def confirm_delta(db,user,delta_id):
 delta=db.get(Delta,delta_id)
 if not delta or delta.recipient!=user.email: raise HTTPException(404,'补差单不存在')
 n=0
 for item in db.query(DeltaItem).filter_by(delta_id=delta.id,status='pending').order_by(DeltaItem.id).all():
  n+=confirm_item(db,user,item.id)[1]
 return delta,n
def list_deltas(db,user):
 out=[]
 for d in db.query(Delta).filter_by(recipient=user.email).order_by(Delta.id.desc()).limit(100).all():
  items=[row(x) for x in db.query(DeltaItem).filter_by(delta_id=d.id).order_by(DeltaItem.id).all()]
  out.append({**row(d),'items':items})
 return out
def reconcile(db,user):
 runs=db.query(Run).filter(Run.approved==True,Run.status=='completed').order_by(Run.id).all()
 latest={}
 for run in runs: latest[stream_key(run)]=run
 streams=[]
 for stream,run in latest.items():
  period,version=stream_of(run)
  target={}
  for r in (run.result or {}).get('rows',[]): target[group_key(r)]=r
  ledgers={x.group_key:x for x in db.query(GroupLedger).filter_by(recipient=user.email,stream=stream).all()}
  pendings={}
  for p in db.query(DeltaItem).filter_by(recipient=user.email,stream=stream,status='pending').all(): pendings[p.group_key]=pendings.get(p.group_key,0)+1
  groups=[];tn=td=tl=rn=rd=rl=0
  for key in sorted(set(target)|set(ledgers)):
   led=ledgers.get(key);r=target.get(key)
   ln,ld,ll=(led.num_total,led.den_total,led.lot_total) if led else (0,0,0)
   gn,gd,gl=(r['分子合计'],r['分母合计'],r['批数']) if r else (0,0,0)
   groups.append({'group_key':key,'group_info':(led.group_info if led else None) or group_of(r),'confirmed_run_id':led.confirmed_run_id if led else 0,'ledger':{'分子':ln,'分母':ld,'批数':ll},'report':{'分子':gn,'分母':gd,'批数':gl},'diff_num':ln-gn,'diff_den':ld-gd,'pending':pendings.get(key,0)})
   tn+=ln;td+=ld;tl+=ll;rn+=gn;rd+=gd;rl+=gl
  streams.append({'stream':stream,'period':period,'policy_version':version,'latest_run_id':run.id,'latest_run_name':run.name,'groups':groups,'total':{'ledger_num':tn,'ledger_den':td,'ledger_lot':tl,'report_num':rn,'report_den':rd,'report_lot':rl,'diff_num':tn-rn,'diff_den':td-rd},'pending':sum(pendings.values()),'balanced':tn==rn and td==rd})
 return {'streams':streams}
def delta_csv(delta,items):
 stream=io.StringIO();w=csv.writer(stream)
 w.writerow(['补差单号','目标报告','期间','口径版本','日期','试制线','班次','基线报告','分子净变动','分母净变动','批数净变动','状态','确认时间'])
 for it in items:
  w.writerow([delta.id,delta.run_id,delta.period,delta.policy_version,it.group_info['日期'],it.group_info['试制线'],it.group_info['班次'],it.base_run_id or '从零',it.num_delta,it.den_delta,it.lot_delta,'已确认' if it.status=='confirmed' else '待确认',datetime.fromtimestamp(it.confirmed_at,CN).strftime('%Y-%m-%d %H:%M:%S') if it.confirmed_at else ''])
 return '\ufeff'+stream.getvalue()
