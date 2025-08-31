import csv
from datetime import datetime

from sqlalchemy.sql.functions import count

from app.database import SessionLocal
from app.models.PhoneCheckInfo import PhoneCheckInfo


def import_jobs_from_csv(phone: list, file_name: str, run_date: datetime):
    session = SessionLocal()
    try:
            has_data = False
            imported_count = 0
            skipped_count = 0
            phoneExists = []

            for sdt in phone:
                has_data = True

                # # validate số điện thoại
                # if not sdt:
                #     print("Bỏ qua dòng vì không có số điện thoại:", row)
                #     skipped_count += 1
                #     continue

                # kiểm tra số điện thoại đã tồn tại
                phoneCheckInfo_exists = session.query(PhoneCheckInfo).filter_by(sdt=sdt).first()
                if phoneCheckInfo_exists:
                    print(f"Số điện thoại {sdt} đã tồn tại, bỏ qua")
                    phoneExists.append(sdt)
                    continue

                # tạo mới record
                phoneCheckInfo = PhoneCheckInfo(
                    file_name=file_name,
                    sdt=sdt,
                    import_date=datetime.now(),
                    status="PENDING",
                    is_update=0,
                    run_date=run_date
                )
                session.add(phoneCheckInfo)
                imported_count += 1

            if has_data:
                session.commit()
                if phoneExists:
                    return {
                        "success": False,
                        "status": "phoneExists",
                        "message": f"Số điện thoại đã tồn tại: {phoneExists}",
                    }
                else:
                    return {
                        "success": True,
                        "imported": imported_count,
                        "skipped": skipped_count
                    }
            return {
                "success": False,
                "status": "noData",
                "message": "File CSV không có dữ liệu"
            }

    except Exception as e:
        print(f"Error importing jobs from CSV: {e}")
        session.rollback()
        return {
            "success": False,
            "message": str(e)
        }
    finally:
        session.close()

def get_phone_check_info_by_filename(file_name: str):
    session = SessionLocal()
    phone_list = session.query(PhoneCheckInfo.sdt, PhoneCheckInfo.status).filter_by(file_name=file_name).all()
    session.close()
    if(phone_list == None):
        return "Not found"
    else:
        phone_list = [{"sdt": r[0], "status": r[1]} for r in phone_list]
    return phone_list

def get_list_file():
    session = SessionLocal()
    phone_list = session.query(PhoneCheckInfo.file_name,PhoneCheckInfo.run_date,count(PhoneCheckInfo.sdt), PhoneCheckInfo.import_date).group_by(PhoneCheckInfo.file_name,PhoneCheckInfo.import_date,PhoneCheckInfo.run_date).all()
    session.close()
    if (phone_list == None):
        return "Not found"
    else:
        phone_list = [{"file_name": r[0], "run_date": r[1], "count":r[2], "import_date":r[3]} for r in phone_list]
    return phone_list