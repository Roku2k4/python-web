from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(100), primary_key=True, index=True, nullable=False)
    phone = Column(String(12))
    customer_name = Column(String(100))
    customer_info = Column(Text)
    transaction_type = Column(String(100))
    req_info = Column(Text)
    resp_info = Column(Text)
    status = Column(Integer, nullable=False, default=0)  # 0: mới tạo, 1: thành công,...
    user_id = Column(Integer, nullable=False)
    transaction_date = Column(DateTime, default=datetime.now(), nullable=False)
    source_type = Column(String(20), default="0")  # 0: mặc định
    device_id = Column(String(100))
    register_device_main = Column(Integer, default=0)
