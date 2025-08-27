# worker.py
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.sql import text, func
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base
from datetime import datetime
from app.database import SessionLocal
from fastapi import APIRouter, Depends, FastAPI
from app.models.PhoneCheckInfo import PhoneCheckInfo, PhoneCheckStatus


app = FastAPI()

def send_sms1(phone):  # thông báo
    message = """
  SIM của quý khách sẽ tạm khóa 1 chiều từ ngày dd/mm/2025 do sim của Quý khách chưa cập nhật thông tin chính chủ.
  Vui lòng cập nhật thông tin qua một trong các hình thức sau để không bị gián đoạn dịch vụ:
- Tải App My iTel để cập nhật: https://myitel.onelink.me/1Wbg/download
- Liên hệ CSKH qua Zalo Mạng di động iTel: https://zalo.me/itelvn
- Quý khách đã cập nhật thông tin chính chủ vui lòng bỏ qua tin nhắn. CSKH: Gọi 0877087087 (0đ).
Trân trọng!"""
    print(f"[SMS] Gửi đến {phone}: {message}")


def send_sms2(phone):  # thông báo khóa c1
    message = """
    SIM của quý khách sẽ tạm khóa 1 chiều từ ngày dd/mm/2025 do sim của Quý khách chưa cập nhật thông tin chính chủ. Vui lòng cập nhật thông tin qua một trong các hình thức sau để không bị gián đoạn dịch vụ:
- Tải App My iTel để cập nhật: https://myitel.onelink.me/1Wbg/download
- Liên hệ CSKH qua Zalo Mạng di động iTel: https://zalo.me/itelvn
- Quý khách đã cập nhật thông tin chính chủ vui lòng bỏ qua tin nhắn. CSKH: Gọi 0877087087 (0đ).
Trân trọng!"""
    print(f"[SMS] Gửi đến {phone}: {message}")


def send_sms3(phone):  # thông báo khóa c2
    message = """
    SIM của Quý khách chưa cập nhật thông tin chính chủ theo quy định, SIM sẽ bị khóa 2 chiều vào ngày dd/mm/2025 và thu hồi hoàn toàn, thanh lý hợp đồng sau 05 ngày kể từ ngày khóa 2 chiều.
    Trân trọng!”"""
    print(f"[SMS] Gửi đến {phone}: {message}")



def process_jobs1():

    session = SessionLocal()
    now = datetime.now()
    jobs = session.query(PhoneCheckInfo).filter(
        PhoneCheckInfo.is_update == False,
        PhoneCheckInfo.run_date <= now
    ).all()

    jobs2 = session.query(PhoneCheckInfo).filter(
        PhoneCheckInfo.is_update == True,
    ).all()

    for job in jobs:
        try:
            if (job.run_date + timedelta(days=14)).date() == now.date():
                if now.hour == 21:
                    job.status = "LOCK_1C"
                    session.commit()


            elif (job.run_date + timedelta(days=29)).date() == now.date():
                if now.hour == 17:
                    # gọi hàm khóa c2
                    job.status = "LOCK_1C"
                    session.commit()

            elif (job.run_date + timedelta(days=34)).date() == now.date():
                if now.hour == 17:
                    # gọi hàm thu hồi
                    pass
        except Exception as e:
            print("Lỗi khi xử lý job1:", e)
            session.rollback()

    for job2 in jobs2:
        if job2.status == PhoneCheckStatus.LOCK_1C:
            job2.status = PhoneCheckStatus.UPDATED
            #goi haam mo khoa C1
            session.commit()
        elif job2.status == PhoneCheckStatus.LOCK_2C:
            job2.status = PhoneCheckStatus.UPDATED
            # goi ham mo khoa C2
            session.commit()
        elif job2.status == PhoneCheckStatus.PENDING:
            job2.status = PhoneCheckStatus.UPDATED
            session.commit()
    session.close()
    
def process_jobs2():
    session = SessionLocal()
    now = datetime.now()
    jobs = session.query(PhoneCheckInfo).filter(
        PhoneCheckInfo.is_update == False,
        PhoneCheckInfo.run_date <= now
    ).all()

    for job in jobs:
        try:
            if (
                job.run_date + timedelta(days=4) >= now
                or job.run_date + timedelta(days=12) <= now
                and job.run_date + timedelta(days=14) > now
            ):
                if job.is_update == False:
                    send_sms1(job.sdt)

            elif (job.run_date + timedelta(days=14)).date() == now.date():
                send_sms2(job.sdt)

            elif job.run_date + timedelta(days=27) <= now and job.run_date + timedelta(days=29) > now:
                if job.is_update == False:
                    send_sms2(job.sdt)

            elif (job.run_date + timedelta(days=29)).date() == now.date():
                if job.is_update == False:
                    send_sms3(job.sdt)

        except Exception as e:
            print("Lỗi khi xử lý job2:", e)
            session.rollback()

    session.close()

def has_new_data():
    with SessionLocal() as session:
        last_import_date = session.execute(
            text("SELECT MAX(import_date) FROM phone_check_info")
        ).scalar()
    if last_import_date >= datetime.now() - timedelta(minutes=1):
        return True
    return False


def schedule_jobs(scheduler):
    print(" Reset lại job1 và job2")

    scheduler.remove_all_jobs()  # xoá job cũ
    #
    # session = SessionLocal()
    # end_date = session.query(func.max(PhoneCheckInfo.run_date)).scalar()
    # session.close()
    #
    # if not end_date:
    #     end_date = datetime.now() + timedelta(days=1)  # fallback

    scheduler.add_job(
        process_jobs1,
        CronTrigger(second="*/3"),
        id="job1",
        replace_existing=True,
    )
    scheduler.add_job(
        process_jobs2,
        CronTrigger(hour=8, minute=0),
        id="job2",
        replace_existing=True,
    )


scheduler = BackgroundScheduler()
scheduler.start()

schedule_jobs(scheduler)

try:
    while True:
        time.sleep(20)
        if has_new_data():
            print(" Có dữ liệu mới → reset job1, job2")
            schedule_jobs(scheduler)
except KeyboardInterrupt:
    scheduler.shutdown()