# worker.py
import threading
import time
from datetime import datetime
from datetime import timedelta
import random

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
import requests
from sqlalchemy.sql import text

from app.database import SessionLocal
from app.models.PhoneCheckInfo import PhoneCheckInfo, PhoneCheckStatus
from app.models.Transactions import Transaction

app = FastAPI()

def convert_phone_number(sdt: str):
    sdt = sdt.strip()
    if sdt.startswith("0"):
        return "84" + sdt[1:]
    elif sdt.startswith("84"):
        return sdt

def provisioning_service(sdt: str, service: str, action: str, comment: str):
    url = "http://10.155.65.77:80/api/integration/vnpt/provisioning-service"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "e90dd9c9-1436-41ad-9d79-0af79e8fd8f4",
        "User": "test",
        "Service": "WEB_CRM"
    }
    payload = {
        "msisdn": convert_phone_number(sdt),
        "service": service,
        "action": action,
        "comment": comment
    }
    try:
        response = requests.post(url, json=payload, headers=headers)

        # parse JSON
        data = response.json()

        print("HTTP Status Code:", response.status_code)
        print("API Code:", data.get("code"))
        print("API Message:", data.get("message"))
        print("API Result:", data.get("result"))

        return {
            "http_status": response.status_code,
            "api_code": data.get("code"),
            "api_message": data.get("message"),
            "api_result": data.get("result"),
        }
    except Exception as e:
        print("Lỗi khi gọi API:", e)



def reprocess_service(sdt: str, comment: str):
    url = "http://10.155.65.77:80/api/integration/vnpt/sps-can-subscriber"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "e90dd9c9-1436-41ad-9d79-0af79e8fd8f4",
        "User": "test",
        "Service": "WEB_CRM"
    }
    payload = {
        "msisdn": convert_phone_number(sdt),
        "comment": comment
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        print("Status code:", response.status_code)

        # parse JSON thay vì in raw text
        data = response.json()
        print("Code:", data.get("code"))
        print("Message:", data.get("message"))
        print("RequestId:", data.get("requestId"))
        print("TotalRecords:", data.get("totalRecords"))
        print("Result:", data.get("result"))
        print("Extra:", data.get("extra"))

    except Exception as e:
        print("Lỗi khi gọi API:", e)


def send_sms(sdt: str, message: str):
    url = "http://10.204.128.152/api/sms/outbound-sms/itel"
    params = {
        "source_ton": 5,
        "source_npi": 1,
        "ucs": "true",
        "source": "8968",
        "destination": convert_phone_number(sdt),
        "text": f"[CSKH iTel] {message}"
    }
    headers = {
        "Authorization": "Basic aXRlbDplODJkZjY2OGExMTYwZmFmMDBhNDRiMDhkNjczNGY2Yw=="
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        data = response.json()

        if isinstance(data, dict):  # Trường hợp API trả về object
            print("[SEND_SMS] Object response:", data)
        elif isinstance(data, list):  # Trường hợp API trả về list
            print("[SEND_SMS] List response:", data)
            if len(data) > 0:
                print("[SEND_SMS] ID nhận được:", data[0])  # lấy phần tử đầu tiên
        else:
            print("[SEND_SMS] Response không rõ dạng:", data)

    except Exception as e:
        print("[SEND_SMS] Lỗi khi gọi API:", e)


def check_transaction_status():

    session = SessionLocal()
    job_trans = session.query(Transaction).filter(Transaction.status == 1).all()
    if job_trans == None:
        return "Not found"
    for job in job_trans:
        job_check = session.query(PhoneCheckInfo).filter(PhoneCheckInfo.sdt == job.phone).first()
        if job_check != None:
            if job_check.run_date <= job.transaction_date <= job_check.run_date + timedelta(days=34) and job_check.is_update == 0:
                job_check.is_update = True
                session.commit()
    session.close()
    return None


def process_jobs1():
    session = SessionLocal()
    now = datetime.now()
    jobs = session.query(PhoneCheckInfo).filter(
        PhoneCheckInfo.is_update == False,
        PhoneCheckInfo.run_date <= now
    ).all()



    for job in jobs:
        try:
            if (job.run_date + timedelta(days=14)).date() == now.date():
                if now.hour == 17:
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
                    session.commit()
        except Exception as e:
            print("Lỗi khi xử lý job1:", e)
            session.rollback()

    jobs2 = session.query(PhoneCheckInfo).filter(
        PhoneCheckInfo.is_update == True,
    ).all()

    for job2 in jobs2:
        if job2.status == PhoneCheckStatus.LOCK_1C:
            provisioning_service(job2.sdt, "oc", "on", "mở khóa 1 chiều")
            job2.status = PhoneCheckStatus.UPDATED
            print(provisioning_service(job2.sdt, "oc", "on", "mở khóa 1 chiều"))
            #goi ham mo khoa C1
            session.commit()
        elif job2.status == PhoneCheckStatus.LOCK_2C:
            provisioning_service(job2.sdt, "ic", "on", "mở khóa 2 chiều")
            job2.status = PhoneCheckStatus.UPDATED
            print(provisioning_service(job2.sdt, "ic", "on", "mở khóa 1 chiều"))
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
                    # rand_time = datetime.now().replace(hour=11, minute=9, second=1, microsecond=0)
                    delay = (rand_time - now).total_seconds()
                    message = f"""
                      SIM của quý khách sẽ tạm khóa 1 chiều từ ngày {job.run_date + timedelta(days=14)} do sim của Quý khách chưa cập nhật thông tin chính chủ.
                      Vui lòng cập nhật thông tin qua một trong các hình thức sau để không bị gián đoạn dịch vụ:
                    - Tải App My iTel để cập nhật: https://myitel.onelink.me/1Wbg/download
                    - Liên hệ CSKH qua Zalo Mạng di động iTel: https://zalo.me/itelvn
                    - Quý khách đã cập nhật thông tin chính chủ vui lòng bỏ qua tin nhắn. CSKH: Gọi 0877087087 (0đ).
                    Trân trọng!"""
                    if delay > 0:
                        print(f"[SCHEDULE] Tạo Timer sau {delay:.2f} giây để gửi SMS cho {job.sdt} lúc {rand_time}")
                        threading.Timer(delay, send_sms, args=[job.sdt, message]).start()
                    else:
                        print(f"[SCHEDULE] Thời gian {rand_time} đã qua, không gửi SMS cho {job.sdt}")

                if(job.run_date + timedelta(days=27) <= now <= job.run_date + timedelta(days=29)):
                    if random.choice([True, False]):
                        rand_time = random_time(8, 10)
                    else:
                        rand_time = random_time(13, 16)
                    # rand_time = datetime.now().replace(hour=9, minute=10, second=0, microsecond=0)
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



def schedule_jobs(scheduler: BackgroundScheduler):
    print("Bắt đầu nhận job")

    scheduler.remove_all_jobs()  # xoá job cũ

    scheduler.add_job(
        process_jobs1,
        CronTrigger(second="*/3"),
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
        # CronTrigger(second="*/3"),
        id="job2",
        replace_existing=True,
    )

