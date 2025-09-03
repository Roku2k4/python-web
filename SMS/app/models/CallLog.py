# CREATE TABLE CallLog (
#     id BIGSERIAL PRIMARY KEY,
#     sdt VARCHAR(20) NOT NULL,
#     action_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
#     status VARCHAR(50) NOT NULL,
#     response TEXT,
#     call_count INT DEFAULT 1
# );
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
    call_count = Column(Integer, default=1, nullable=False)      # số lần lặp lại
