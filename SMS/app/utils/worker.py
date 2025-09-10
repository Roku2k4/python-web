# worker.py
import random
import threading
import time
from datetime import datetime
from datetime import timedelta
from sys import exception
from time import sleep
from zoneinfo import ZoneInfo
from sqlalchemy import func
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from sqlalchemy import desc
from app.database import SessionLocal
from app.models.CallLog import CallLog
from app.models.PhoneCheckInfo import PhoneCheckInfo, PhoneCheckStatus
from app.models.Transactions import Transaction
app = FastAPI()

#def convert_phone_number(sdt: str):
#    sdt = sdt.strip()
#    if sdt.startswith("0"):
#        return sdt
#    elif sdt.startswith("84"):
#        return "0" + sdt[2:]
#    elif sdt.startswith("+84"):
#        return "0"+ sdt[3:]
#   return sdt

def convert_phone_number(sdt: str):
    sdt = sdt.strip()
    if sdt.startswith("0"):
        return "84" + sdt[1:]
    elif sdt.startswith("84"):
        return sdt
    elif sdt.startswith("+84"):
        return sdt[1:]

def _is_success(http_status: int, api_code) -> bool:
    """Chỉ coi là thành công khi http = 200 và code = 200 (số hoặc chuỗi '200')."""
    try:
        return int(http_status) == 200 and int(api_code) == 200
    except Exception:
        return False

def provisioning_service(sdt: str, service: str, action: str, comment: str):
    url = "http://10.155.65.77:80/api/integration/vnpt/provisioning-service/"
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

    session = SessionLocal()
    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        data = response.json()

        http_status = response.status_code
        api_code = data.get("code")
        api_msg = data.get("message")
        ok = _is_success(http_status, api_code)

        session.add(CallLog(
            sdt=sdt,
            action_time=now,
            status="SUCCESS" if ok else "FAILED",
            response=f"[PROVISIONING] msg was send"
        ))
        session.commit()

        return {
            "ok": True, "error": "200", "out": True
        }
    except Exception as e:
        log = CallLog(
            sdt=sdt,
            action_time=now,
            status="FAILED",
            response=f"[PROVISIONING] Failed to call API"
        )
        session.add(log)
        session.commit()
        return {"ok": False, "error": str(e), "out": False}
    finally:
        session.close()


def reprocess_service(sdt: str, comment: str):
    url = "http://10.155.65.77:80/api/integration/vnpt/sps-can-subscriber/"
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

    session = SessionLocal()
    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        data = response.json()

        http_status = response.status_code
        api_code = data.get("code")
        api_msg = data.get("message")
        ok = _is_success(http_status, api_code)

        session.add(CallLog(
            sdt=sdt,
            action_time=now,
            status="SUCCESS" if ok else "FAILED",
            response=f"[REPROCESS] msg was send"
        ))
        session.commit()

        return {"ok": True, "error": "200", "out": True}
    except Exception as e:
        log = CallLog(
            sdt=sdt,
            action_time=now,
            status="FAILED",
            response=f"[REPROCESS] Failed to call API"
        )
        session.add(log)
        session.commit()
        return {"ok": False, "error": str(e), "out": True}
    finally:
        session.close()


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

    session = SessionLocal()
    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()

        # API SMS có thể trả list hoặc dict; bạn yêu cầu rule cứng: http=200 & code=200
        http_status = response.status_code
        api_code = None
        if isinstance(data, dict):
            api_code = data.get("code")
            api_msg = data.get("message")
        else:
            # nếu list hoặc dạng khác, coi như không đạt rule "code=200"
            api_msg = str(data)[:200]

        ok = _is_success(http_status, api_code)

        session.add(CallLog(
            sdt=sdt,
            action_time=now,
            status="SUCCESS" if ok else "FAILED",
            response=f"[SMS] http={http_status} | code={api_code} | msg={api_msg}"
        ))
        session.commit()

        return {"ok": ok, "http_status": http_status, "api_code": api_code, "api_message": api_msg}
    except Exception as e:
        session.add(CallLog(
            sdt=sdt,
            action_time=now,
            status="FAILED",
            response=f"[SMS] exception={str(e)}"
        ))
        session.commit()
        return {"ok": False, "error": str(e)}
    finally:
        session.close()



def check_transaction_status():
    session = SessionLocal()
    job_trans = session.query(Transaction).filter(Transaction.status == 1).all()
    if job_trans == None:
        return "Not found"
    for job in job_trans:
        job_check = session.query(PhoneCheckInfo).filter(PhoneCheckInfo.sdt == job.phone).first()
        if job_check != None:
            if job_check.run_date.date() <= job.transaction_date.date() <= job_check.run_date.date() + timedelta(days=34) and job_check.is_update == 0 and job.transaction_type == "UPDATE_INFOS":
                job_check.is_update = True
                session.commit()
    session.close()
    return None

def check_5_fail(session, phone) -> bool:
    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    since = now - timedelta(minutes=5)
    # Lấy 5 bản ghi mới nhất kể từ 'since'
    logs = (session.query(CallLog)
            .filter(CallLog.sdt == phone)
            .filter(CallLog.action_time >= since)
            .order_by(desc(CallLog.action_time), desc(CallLog.response))
            .limit(5)
            .all())

    if len(logs) < 5:
        return False

    # Nếu cả 5 đều FAILED => dừng
    return all(log.status == "FAILED" for log in logs)

def process_jobs1(scheduler: BackgroundScheduler): # hàm này tao bao thm một lớp while True để chạy lin tục, kéo xuống exception

    session = SessionLocal()
    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    jobs = session.query(PhoneCheckInfo).filter(
        PhoneCheckInfo.is_update == False,
        PhoneCheckInfo.run_date <= now
    ).all()

    for job in jobs:
        try:
            if (job.run_date + timedelta(days=15)).date() == now.date() and job.status == PhoneCheckStatus.PENDING:
                if 10 <= now.hour <= 17:
                    if check_5_fail(session, job.sdt):
                        session.close()
                        print("hủy lịch do lỗi LOCK 1C 5 lần")
                        scheduler.remove_all_jobs()
                        break
                    check =provisioning_service(job.sdt,"oc","off","QTXLTB có TTTB không đúng QĐ (35)")
                    if check.get("ok")== False:
                        session.close()
                        sleep(30)
                        break
                    job.status = PhoneCheckStatus.LOCK_1C
                    session.commit()

            elif (job.run_date + timedelta(days=30)).date() == now.date() and job.status == PhoneCheckStatus.LOCK_1C:
                if 10 <= now.hour <= 16:
                    if check_5_fail(session, job.sdt):
                        session.close()
                        print("hủy lịch do lỗi LOCK 2C 5 lần")
                        scheduler.remove_all_jobs()
                        break
                    check = provisioning_service(job.sdt, "ic", "off", "QTXLTB có TTTB không đúng QĐ (35)")
                    if check.get("ok") == False:
                        session.close()
                        sleep(30)
                        break
                    job.status = PhoneCheckStatus.LOCK_2C
                    session.commit()

            elif (job.run_date + timedelta(days=35)).date() == now.date() and job.status == PhoneCheckStatus.LOCK_2C:
                if 10 <= now.hour <= 16:
                    if check_5_fail(session, job.sdt):
                        session.close()
                        print("hủy lịch do lỗi REPROCESS 5 lần")
                        scheduler.remove_all_jobs()
                        break
                    check = reprocess_service(job.sdt, "QTXLTB có TTTB không đúng QĐ (35)")
                    if check.get("ok")== False:
                        session.close()
                        sleep(30)
                        break
                    job.status = PhoneCheckStatus.REPROCESS
                    session.commit()
        except Exception as e:
            log_session = SessionLocal()
            try:
                log = CallLog(
                    sdt=job.sdt,
                    action_time=now,
                    status="FAILED",
                    response=str(e),
                )
                log_session.add(log)
                log_session.commit()
                # Kiểm tra stop_number >=5 thì dừng toàn bộ
                if check_5_fail(session, log.sdt):
                    session.close()
                    print("hủy lịch do lỗi ở hàm process_job1 5 lần")
                    scheduler.remove_all_jobs()
                    break
                # Ngủ 30 giây trước khi tiếp tục vòng lặp
                print(f"Lỗi xảy ra, nghỉ 30 giây trước khi tiếp tục...")
                time.sleep(30)
                break
            except Exception as log_err:
                print("Lỗi khi ghi CallLog:", log_err)
                log_session.rollback()
            finally:
                log_session.close()


    jobs2 = session.query(PhoneCheckInfo).filter(
        PhoneCheckInfo.is_update == True,
    ).all()

    for job2 in jobs2:
        if job2.status == PhoneCheckStatus.LOCK_1C:
            provisioning_service(job2.sdt, "oc", "on", "mở khóa 1 chiều")
            job2.status = PhoneCheckStatus.UPDATED
            print(provisioning_service(job2.sdt, "oc", "on", "mở khóa 1 chiều"))
            # goi ham mo khoa C1
            session.commit()
        elif job2.status == PhoneCheckStatus.LOCK_2C:
            provisioning_service(job2.sdt, "ic", "on", "mở khóa 2 chiều")
            provisioning_service(job2.sdt, "oc", "on", "mở khóa 1 chiều")
            job2.status = PhoneCheckStatus.UPDATED
            print(provisioning_service(job2.sdt, "ic", "on", "mở khóa 1 chiều"))
            # goi ham mo khoa C2
            session.commit()
        elif job2.status == PhoneCheckStatus.PENDING:
            job2.status = PhoneCheckStatus.UPDATED
            session.commit()
    session.close()

def random_time(time_start: int, time_end: int):
    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    start = now.replace(hour=time_start, minute=0, second=0, microsecond=0)
    end = now.replace(hour=time_end, minute=0, second=0, microsecond=0)
    random_seconds = random.randint(0, int((end - start).total_seconds()))
    random_times = start + timedelta(seconds=random_seconds)
    return random_times

def process_jobs2(scheduler: BackgroundScheduler):
    session = SessionLocal()
    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    jobs = session.query(PhoneCheckInfo).filter(
        PhoneCheckInfo.is_update == False,
        PhoneCheckInfo.run_date <= now
    ).all()

    for job in jobs:
        t0 = job.run_date.date()
        try:
            if (job.status == PhoneCheckStatus.UPDATED and t0 <= now.date() <= t0 + timedelta(days=30)):
                continue

            elif (job.is_update == False):

                if (t0 <= now.date() <= t0 + timedelta(days=4) or t0 + timedelta(
                        days=13) <= now.date() <= t0 + timedelta(days=15)):
                    # rand_time = random_time(8, 10)
                    # delay = (rand_time - now).total_seconds()
                    delay = 0
                    message = f"""SIM của quý khách sẽ tạm khóa 1 chiều từ ngày {(t0 + timedelta(days=15)).strftime("%d/%m/%Y")} do thông tin thuê bao không chính chủ. Vui lòng chuẩn hóa thông tin qua một trong các hình thức sau để không bị gián đoạn dịch vụ:
            - Tải App My iTel để cập nhật: https://myitel.onelink.me/1Wbg/download, chọn “Chuyển quyền sử dụng”
            - Liên hệ CSKH qua Zalo Mạng di động iTel: https://zalo.me/itelvn
            - Quý khách đã chuẩn hóa thông tin chính chủ vui lòng bỏ qua tin nhắn. CSKH: Gọi 0877087087 (0đ).
            Trân trọng!"""
                    if delay >= 0:
                        # print(f"[SCHEDULE] Tạo Timer sau {delay:.2f} giây để gửi SMS cho {job.sdt} lúc {randtime}")
                        print(f"Đã gửi SMS tới {job.sdt} lúc:, {now.hour}")
                        threading.Timer(delay, send_sms, args=[job.sdt, message]).start()
                    else:
                        # print(f"[SCHEDULE] Thời gian {rand_time} đã qua, không gửi SMS cho {job.sdt}")
                        print(f"Đã gửi SMS tới {job.sdt} lúc:, {now.hour}")

                if (t0 + timedelta(days=28) <= now.date() <= t0 + timedelta(days=30)):
                    # if random.choice([True, False]):
                    #     rand_time = random_time(8, 10)
                    # else:
                    #     rand_time = random_time(13, 16)
                    # delay = (rand_time - now).total_seconds()
                    delay = 0
                    message = f"""iTel: SIM của Quý khách chưa chuẩn hóa thông tin chính chủ theo quy định, SIM sẽ bị khóa 2 chiều vào ngày {(t0 + timedelta(days=30)).strftime("%d/%m/%Y")} và thu hồi hoàn toàn, thanh lý hợp đồng sau 05 ngày kể từ ngày khóa 2 chiều.
            Trân trọng!”"""
                    threading.Timer(delay, send_sms, args=[job.sdt, message]).start()
                    # print(f"Đã gửi SMS tới {job.sdt} lúc:, {rand_time}")
                    print(f"Đã gửi SMS tới {job.sdt} lúc:, {now.hour}")

        except Exception as e:
            # Đếm số lần đã có trong CallLog với sdt
            # Ghi log lỗi
            log_session = SessionLocal()
            try:
                log = CallLog(
                    sdt=job.sdt,
                    action_time=now,
                    status="FAILED",
                    response=str(e),
                )
                log_session.add(log)
                log_session.commit()
                # Kiểm tra nếu có số nào call_count == 5 thì dừng toàn bộ
                stop_number = log_session.query(func.count(CallLog.response)).filter(
                    CallLog.response == log.response).scalar()
                print("stop_number = ", stop_number)
                if stop_number >= 5:
                    print(f" {str(e)} đã bị lỗi 5 lần. Dừng toàn bộ tiến trình.")
                    log_session.close()
                    session.close()
                    scheduler.remove_all_jobs()
                    print("hủy lịch")
                    return
                # Ngủ 30 giây trước khi tiếp tục vòng lặp
                print(f"Lỗi xảy ra, nghỉ 30 giây trước khi tiếp tục...")
                time.sleep(30)
            except Exception as log_err:
                print("Lỗi khi ghi CallLog:", log_err)
                log_session.rollback()
            finally:
                log_session.close()
            # session.rollback()
    session.close()

def schedule_jobs(scheduler: BackgroundScheduler):
    print("Bắt đầu nhận job")

    scheduler.remove_all_jobs()  # xoá job cũ

    scheduler.add_job(
        process_jobs1,
        CronTrigger(second="*/3"),
        id="job1",
        replace_existing=True,
        args=[scheduler],
    )
    # scheduler.add_job(
    #     check_transaction_status,
    #     CronTrigger(second="*/3"),
    #     id="job_check_trans",
    #     replace_existing=True,
    # )
    # scheduler.add_job(
    #     process_jobs2,
    #     # CronTrigger(hour=7, minute=59),
    #     CronTrigger(minute="*/5"),
    #     # CronTrigger(second="*/5"),
    #     id="job2",
    #     replace_existing=True,
    #     args=[scheduler],
    #     )

