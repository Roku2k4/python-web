from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base

class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    sdt = Column(String(20), nullable=False)       # số thuê bao
    action_time = Column(DateTime, default=datetime.now, nullable=False)  # thời gian gọi
    status = Column(String(50), nullable=False)                  # trạng thái: SUCCESS / FAILED
    response = Column(Text)                                      # response trả về