// API实体字段约定：来源{id,natural_key,data}、口径{id,version,data}、报告{id,status,snapshot,checksum,result,approved}、计划{next_at,enabled}、补差单{id,recipient,period,policy_version,run_id,items[{group,num_delta,den_delta,lot_delta,status}]}、对账{streams[{groups,total,balanced}]}。
export const ENTITY_KEYS=['sources','policies','runs','schedules','deliveries','deltas'];
