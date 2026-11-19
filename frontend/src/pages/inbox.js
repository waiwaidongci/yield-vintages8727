import {heading} from '../components/common/header.js';import {esc,time,fmt} from '../utils/format.js';import {DELTA} from '../constants/enums.js';
const signed=v=>`<b class="${v<0?'neg':'pos'}">${v>0?'+':''}${fmt(v)}</b>`;
const diff=v=>v?`<b class="diff">${fmt(v)}</b>`:'0';
function itemRows(items){return items.map(i=>`<tr><td>${esc(i.group_info['日期'])}</td><td>${esc(i.group_info['试制线'])}</td><td>${esc(i.group_info['班次'])}</td><td>${signed(i.num_delta)}</td><td>${signed(i.den_delta)}</td><td>${signed(i.lot_delta)}</td><td>${i.base_run_id?'#'+i.base_run_id:'从零'}</td><td>#${i.target_run_id}</td><td>${DELTA[i.status]||esc(i.status)}</td><td>${i.status==='pending'?`<button class="confirm-item" data-id="${i.id}">确认入账</button>`:''}</td></tr>`).join('')}
function deltaCard(x,onlyPending){
 const items=onlyPending?x.items.filter(i=>i.status==='pending'):x.items;
 const done=x.items.filter(i=>i.status==='confirmed').length;
 return `<article class="delta"><header><span>${time(x.created)}</span><h3>补差单 #${x.id} → 报告 #${x.run_id}</h3><div class="actions"><button class="confirm-delta" data-id="${x.id}" ${done===x.items.length?'disabled':''}>整单确认</button><button class="delta-export" data-id="${x.id}">下载补差 CSV</button></div><p>期间 ${esc(x.period)} · 口径 ${esc(x.policy_version)} · ${done}/${x.items.length} 项已确认</p></header>${items.length?`<div class="table-wrap"><table><thead><tr><th>日期</th><th>试制线</th><th>班次</th><th>分子净变动</th><th>分母净变动</th><th>批数净变动</th><th>基线报告</th><th>目标报告</th><th>状态</th><th></th></tr></thead><tbody>${itemRows(items)}</tbody></table></div>`:'<p class="empty">本次交付无净变动，无需入账。</p>'}</article>`}
function reconcileBlock(s){
 const row=g=>`<tr><td>${esc(g.group_info['日期'])}</td><td>${esc(g.group_info['试制线'])}</td><td>${esc(g.group_info['班次'])}</td><td>${fmt(g.ledger['分子'])}</td><td>${fmt(g.report['分子'])}</td><td>${diff(g.diff_num)}</td><td>${fmt(g.ledger['分母'])}</td><td>${fmt(g.report['分母'])}</td><td>${diff(g.diff_den)}</td><td>${g.pending||''}</td></tr>`;
 const t=s.total;
 return `<section class="reconcile"><h3>期间 ${esc(s.period)} · 口径 ${esc(s.policy_version)} · 最新复核报告 #${s.latest_run_id}《${esc(s.latest_run_name)}》 ${s.balanced?'<span class="status completed">账实一致</span>':`<span class="status failed">差异未平 · 待确认 ${s.pending} 项</span>`}</h3><div class="table-wrap"><table><thead><tr><th>日期</th><th>试制线</th><th>班次</th><th>已确认分子</th><th>报告分子</th><th>分子差异</th><th>已确认分母</th><th>报告分母</th><th>分母差异</th><th>待确认</th></tr></thead><tbody>${s.groups.map(row).join('')}<tr class="total"><td>合计</td><td></td><td></td><td>${fmt(t.ledger_num)}</td><td>${fmt(t.report_num)}</td><td>${diff(t.diff_num)}</td><td>${fmt(t.ledger_den)}</td><td>${fmt(t.report_den)}</td><td>${diff(t.diff_den)}</td><td>${s.pending||''}</td></tr></tbody></table></div></section>`}
export function inbox(c,d){
 const deltas=d.deltas||[];
 const pending=deltas.filter(x=>x.items.some(i=>i.status==='pending'));
 const streams=(d.reconcile&&d.reconcile.streams)||[];
 return heading('DELTA INBOX / 06','补差收件箱','同期间同口径的报告按组交付分子/分母净变动；确认后入账，未确认组随原单挂起，全部确认后累计与最新复核报告一致。')
 +`<h2>待确认项</h2>`+(pending.length?pending.map(x=>deltaCard(x,true)).join(''):'<p class="empty">暂无待确认补差。报告复核后，worker 按组生成净变动补差；未确认组随原单继续挂起，不重复开单。</p>')
 +`<h2>对账 · 已确认累计 vs 最新复核报告</h2>`+(streams.length?streams.map(reconcileBlock).join(''):'<p class="empty">尚无已复核报告，暂无可对账的流。</p>')
 +`<h2>全部补差单</h2>`+(deltas.length?deltas.map(x=>deltaCard(x,false)).join(''):'<p class="empty">暂无补差单。</p>')
}
