# worker.py
import threading
import time
from datetime import datetime
from datetime import timedelta
import random

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, requests
from sqlalchemy.sql import text

from app.database import SessionLocal
from app.models.PhoneCheckInfo import PhoneCheckInfo, PhoneCheckStatus
from app.models.Transactions import Transaction

app = FastAPI()

# def send_sms1(phone):  # thông báo
#     message = """
#   SIM của quý khách sẽ tạm khóa 1 chiều từ ngày dd/mm/2025 do sim của Quý khách chưa cập nhật thông tin chính chủ.
#   Vui lòng cập nhật thông tin qua một trong các hình thức sau để không bị gián đoạn dịch vụ:
# - Tải App My iTel để cập nhật: https://myitel.onelink.me/1Wbg/download
# - Liên hệ CSKH qua Zalo Mạng di động iTel: https://zalo.me/itelvn
# - Quý khách đã cập nhật thông tin chính chủ vui lòng bỏ qua tin nhắn. CSKH: Gọi 0877087087 (0đ).
# Trân trọng!"""
#     print(f"[SMS] Gửi đến {phone}: {message}")


# def send_sms2(phone):  # thông báo khóa 2c
#     message = """
#     SIM của Quý khách chưa cập nhật thông tin chính chủ theo quy định, SIM sẽ bị khóa 2 chiều vào ngày dd/mm/2025 và thu hồi hoàn toàn, thanh lý hợp đồng sau 05 ngày kể từ ngày khóa 2 chiều.
#     Trân trọng!”"""
#     print(f"[SMS] Gửi đến {phone}: {message}")

def provisioning_service(sdt: str, service: str, action: str, comment: str):
    url = "http://10.159.26.88:9000/itel/provisioning-service"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "xxxx"
    }
    payload = {
        "msisdn": sdt,
        "service": service,
        "action": action,
        "comment": comment
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        print("Status code:", response.status_code)
        print("Response:", response.text)
    except Exception as e:
        print("Lỗi khi gọi API:", e)

def reprocess_service(sdt: str, comment: str):
    url = "http://10.159.26.88:9000/itel/sps-can-subscriber"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "xxxx"
    }
    payload = {
        "msisdn": sdt,
        "comment": comment
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        print("Status code:", response.status_code)
        print("Response:", response.text)
    except Exception as e:
        print("Lỗi khi gọi API:", e)

def send_sms(sdt: str, message: str):
    url = "http://10.204.128.152/api/sms/outbound-sms/itel"
    params = {
        "source_ton": 5,
        "source_npi": 1,
        "ucs": "true",
        "source": "8968",
        "destination": sdt,
        "text": f"[CSKH iTel] {message}"
    }
    headers = {
        "Authorization": "Basic aXRlbDplODJkZjY2OGExMTYwZmFmMDBhNDRiMDhkNjczNGY2Yw=="
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        print("Status code:", response.status_code)
        print("Response:", response.text)
    except Exception as e:
        print("Lỗi khi gọi API SMS:", e)

def check_transaction_status():
    # session = SessionLocal()
    # job_check = session.query(PhoneCheckInfo).filter(PhoneCheckInfo.sdt == sdt).first()
    # if job_check == None:
    #     return "Not found"
    # job_trans = session.query(Transaction.status, Transaction.transaction_date).filter(
    #     Transaction.phone == sdt).first()
    # if job_trans == None:
    #     return "Not found"
    # if job_trans.status == 1 and job_check.run_date <= job_trans.transaction_date <= job_check.run_date + timedelta(
    #         days=34 and job_check.is_update == 0):
    #     job_check.is_update = 1
    #     session.commit()

    session = SessionLocal()
    job_trans = session.query(Transaction).filter(Transaction.status == 1).all()
    if job_trans == None:
        return "Not found"
    for job in job_trans:
        job_check = session.query(PhoneCheckInfo).filter(PhoneCheckInfo.sdt == job.phone).first()
        if job_check != None:
            if job_check.run_date <= job.transaction_date <= job_check.run_date + timedelta(days=34) and job_check.is_update == 0:
                job_check.is_update = 1
                session.commit()
    session.close()
    return None


def process_jobs1():
    session = SessionLocal()
    now = datetime.now()
    jobs = session.query(PhoneCheckInfo).filter(
        PhoneCheckInfo.is_update == 0,
        PhoneCheckInfo.run_date <= now
    ).all()

    jobs2 = session.query(PhoneCheckInfo).filter(
        PhoneCheckInfo.is_update == 1,
    ).all()

    for job in jobs:
        try:
            if (job.run_date + timedelta(days=14)).date() == now.date():
                if now.hour == 21:
                    job.status = "LOCK_1C"
                    provisioning_service(job.sdt,"oc","off","khóa 1 chiều")
                    session.commit()


            elif (job.run_date + timedelta(days=29)).date() == now.date():
                if now.hour == 17:
                    job.status = "LOCK_2C"
                    provisioning_service(job.sdt, "ic", "off", "khóa 2 chiều")
                    session.commit()

            elif (job.run_date + timedelta(days=34)).date() == now.date():
                if now.hour == 17:
                    # gọi hàm thu hồi
                    job.status = "REPROCESS"
                    reprocess_service(job.sdt, "ly do huy thue bao")
                    pass
        except Exception as e:
            print("Lỗi khi xử lý job1:", e)
            session.rollback()

    for job2 in jobs2:
        if job2.status == PhoneCheckStatus.LOCK_1C:
            job2.status = PhoneCheckStatus.UPDATED
            provisioning_service(job2.sdt, "oc", "on", "mở khóa 1 chiều")
            #goi ham mo khoa C1
            session.commit()
        elif job2.status == PhoneCheckStatus.LOCK_2C:
            job2.status = PhoneCheckStatus.UPDATED
            provisioning_service(job2.sdt, "ic", "on", "mở khóa 2 chiều")
            # goi ham mo khoa C2
            session.commit()
        elif job2.status == PhoneCheckStatus.PENDING:
            job2.status = PhoneCheckStatus.UPDATED
            session.commit()
    session.close()

def random_time(time_start: int, time_end: int):
    now = datetime.now()
    start = now.replace(hour=time_start, minute=0, second=0, microsecond=0)
    end = now.replace(hour=time_end, minute=0, second=0, microsecond=0)
    random_seconds = random.randint(0, int((end - start).total_seconds()))
    random_times = start + timedelta(seconds=random_seconds)
    return random_times

def process_jobs2():
    session = SessionLocal()
    now = datetime.now()
    jobs = session.query(PhoneCheckInfo).filter(
        PhoneCheckInfo.is_update == False,
        PhoneCheckInfo.run_date <= now
    ).all()

    for job in jobs:
        try:
            if(job.status == PhoneCheckStatus.UPDATED and job.run_date <= now <= job.run_date + timedelta(days=29)):
                continue

            elif(job.is_update == False):
                if(job.run_date <= now <= job.run_date + timedelta(days=4) or job.run_date + timedelta(days=12) <= now <= job.run_date + timedelta(days=14)):
                    rand_time = random_time(8, 10)
                    delay = (rand_time - now).total_seconds()
                    message = f"""
                      SIM của quý khách sẽ tạm khóa 1 chiều từ ngày {job.run_date + timedelta(days=14)} do sim của Quý khách chưa cập nhật thông tin chính chủ.
                      Vui lòng cập nhật thông tin qua một trong các hình thức sau để không bị gián đoạn dịch vụ:
                    - Tải App My iTel để cập nhật: https://myitel.onelink.me/1Wbg/download
                    - Liên hệ CSKH qua Zalo Mạng di động iTel: https://zalo.me/itelvn
                    - Quý khách đã cập nhật thông tin chính chủ vui lòng bỏ qua tin nhắn. CSKH: Gọi 0877087087 (0đ).
                    Trân trọng!"""
                    threading.Timer(delay, send_sms, args=[job.sdt, message]).start()
                    print(f"Đã gửi SMS tới {job.sdt} lúc:, {rand_time}")

                if(job.run_date + timedelta(days=27) <= now <= job.run_date + timedelta(days=29)):
                    if random.choice([True, False]):
                        rand_time = random_time(8, 10)
                    else:
                        rand_time = random_time(13, 16)
                    delay = (rand_time - now).total_seconds()
                    message = f"""
                        SIM của Quý khách chưa cập nhật thông tin chính chủ theo quy định, SIM sẽ bị khóa 2 chiều vào ngày {job.run_date + timedelta(days=29)} và thu hồi hoàn toàn, thanh lý hợp đồng sau 05 ngày kể từ ngày khóa 2 chiều.
                        Trân trọng!”"""
                    threading.Timer(delay, send_sms, args=[job.sdt, message]).start()
                    print(f"Đã gửi SMS tới {job.sdt} lúc:, {rand_time}")

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
        CronTrigger(minute=1),
        id="job1",
        replace_existing=True,
    )
    scheduler.add_job(
        check_transaction_status,
        CronTrigger(second="*/3"),
        id="job_check_trans",
        replace_existing=True,
    )
    scheduler.add_job(
        process_jobs2,
        CronTrigger(hour=7, minute=59),
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