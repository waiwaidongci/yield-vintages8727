from sqlalchemy import Column,Integer,String,JSON,Float
from src.config.database import Base
class Delta(Base):
 __tablename__='delta_deliveries'
 id=Column(Integer,primary_key=True); recipient=Column(String(120)); period=Column(String(120)); policy_version=Column(String(120)); run_id=Column(Integer); due_key=Column(String(500),unique=True); created=Column(Float)
class DeltaItem(Base):
 __tablename__='delta_items'
 id=Column(Integer,primary_key=True); delta_id=Column(Integer); recipient=Column(String(120)); stream=Column(String(250)); group_key=Column(String(250)); group_info=Column(JSON); base_run_id=Column(Integer); target_run_id=Column(Integer); num_delta=Column(Integer); den_delta=Column(Integer); lot_delta=Column(Integer); status=Column(String(20)); confirmed_at=Column(Float); pending_key=Column(String(500),unique=True)
class GroupLedger(Base):
 __tablename__='delta_ledgers'
 id=Column(Integer,primary_key=True); ledger_key=Column(String(500),unique=True); recipient=Column(String(120)); stream=Column(String(250)); group_key=Column(String(250)); group_info=Column(JSON); confirmed_run_id=Column(Integer,default=0); num_total=Column(Integer,default=0); den_total=Column(Integer,default=0); lot_total=Column(Integer,default=0)
