import {request} from './client.js';
const PATHS={sources:'/sources',periods:'/periods',policies:'/policies',runs:'/runs',schedules:'/schedules',deliveries:'/deliveries',deltas:'/deltas',reconcile:'/deltas/reconcile',audits:'/audits'};
export const loadAll=async()=>Object.fromEntries(await Promise.all(Object.entries(PATHS).map(async([k,p])=>[k,await request(p)])));
export const saveSource=(data,id)=>request('/sources'+(id?'/'+id:''),id?'PUT':'POST',{data});
export const savePolicy=data=>request('/policies','POST',{data});
export const submitRun=data=>request('/runs','POST',data);
export const approveRun=(id,note)=>request('/runs/'+id+'/approve','POST',{note});
export const confirmDeltaItem=id=>request('/deltas/items/'+id+'/confirm','POST',{});
export const confirmDelta=id=>request('/deltas/'+id+'/confirm','POST',{});
