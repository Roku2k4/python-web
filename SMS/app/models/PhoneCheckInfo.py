import enum
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Enum trong Python để map với enum trong DB
class PhoneCheckStatus(enum.Enum):
    PENDING = "PENDING"
    LOCK_1C = "LOCK_1C"
    LOCK_2C = "LOCK_2C"
    REPROCESS = "REPROCESS"
    UPDATED = "UPDATED"

class PhoneCheckInfo(Base):
    __tablename__ = "phone_check_info"

    file_name = Column(String(100), nullable=False)
    sdt = Column(String(12),primary_key=True, nullable=False)
    import_date = Column(DateTime, nullable=True)
    status = Column(Enum(PhoneCheckStatus), nullable=False, default=PhoneCheckStatus.PENDING)
    is_update = Column(Boolean, default=False)   # tinyint(1) -> Boolean
    run_date = Column(DateTime, nullable=True)
