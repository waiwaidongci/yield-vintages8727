from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import Response
from src.config.database import database
from src.controllers.auth import current
from src.models.delta import Delta,DeltaItem
from src.services.delta import confirm_item,confirm_delta,reconcile,delta_csv,list_deltas
router=APIRouter()
@router.get('/deltas')
def deltas(db=Depends(database),u=Depends(current)): return list_deltas(db,u)
@router.get('/deltas/reconcile')
def recon(db=Depends(database),u=Depends(current)): return reconcile(db,u)
@router.post('/deltas/items/{id}/confirm')
def confirm_one(id:int,db=Depends(database),u=Depends(current)):
 item,changed=confirm_item(db,u,id)
 return {'id':item.id,'status':item.status,'changed':changed}
@router.post('/deltas/{id}/confirm')
def confirm_all(id:int,db=Depends(database),u=Depends(current)):
 delta,n=confirm_delta(db,u,id)
 return {'id':delta.id,'confirmed':n}
@router.get('/deltas/{id}/csv')
def csv(id:int,db=Depends(database),u=Depends(current)):
 delta=db.get(Delta,id)
 if not delta or delta.recipient!=u.email: raise HTTPException(404,'补差单不存在')
 items=db.query(DeltaItem).filter_by(delta_id=delta.id).order_by(DeltaItem.id).all()
 return Response(delta_csv(delta,items),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="delta-{id}.csv"'})
