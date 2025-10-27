from datetime import datetime, timedelta

from sqlalchemy.sql.functions import count

from app.database import SessionLocal
from app.models.PhoneCheckInfo import PhoneCheckInfo
from app.utils.worker import convert_phone_number

def import_jobs_from_csv(phone: list, file_name: str, run_date: datetime):
    session = SessionLocal()
    if isinstance(run_date, str):
        run_date = datetime.strptime(run_date, '%Y-%m-%d')  # Chuyển chuỗi thành datetime nếu cần

    try:
        has_data = False
        imported_count = 0
        skipped_count = 0
        duplicate_in_file = set()  # Lưu các số trùng trong file
        seen_numbers = set()       # Lưu các số đã gặp

        for sdt in phone:
            has_data = True
            norm_sdt = convert_phone_number(sdt)  # Chuẩn hoá số

            # 🔍 Kiểm tra trùng trong file
            if norm_sdt in seen_numbers:
                print(f"Số điện thoại {norm_sdt} bị trùng trong file, bỏ qua")
                duplicate_in_file.add(norm_sdt)
                skipped_count += 1
                continue
            else:
                seen_numbers.add(norm_sdt)

            # 🟢 Không còn kiểm tra trùng trong DB
            phoneCheckInfo = PhoneCheckInfo(
                file_name=file_name,
                sdt=norm_sdt,
                import_date=datetime.now(),
                status="PENDING",
                is_update=0,
                run_date=run_date
            )
            session.add(phoneCheckInfo)
            imported_count += 1

        if duplicate_in_file:
            # Nếu có số trùng trong file
            return {
                "code": 400,
                "msg": "Có số điện thoại bị trùng trong file, bỏ qua",
                "duplicates": list(duplicate_in_file),
                "total_imported": imported_count,
                "total_skipped": skipped_count
            }

        if has_data:
            session.commit()
            return {
                "code": 200,
                "msg": f"Import file {file_name} thành công",
                "total_imported": imported_count
            }
        else:
            return {
                "code": 400,
                "msg": "File CSV không có dữ liệu"
            }

    except Exception as e:
        print(f"Error importing jobs from CSV: {e}")
        session.rollback()
        return {
            "code": 500,
            "msg": str(e)
        }
    finally:
        session.close()

def get_phone_check_info_by_filename(file_name: str, run_date: datetime = None, import_date: datetime = None):
    session = SessionLocal()
    query = session.query(
        PhoneCheckInfo.sdt,
        PhoneCheckInfo.status
    ).filter(PhoneCheckInfo.file_name == file_name)

    if run_date:
        query = query.filter(PhoneCheckInfo.run_date == run_date)
    if import_date:
        query = query.filter(PhoneCheckInfo.import_date == import_date)

    phone_list = query.all()
    session.close()

    if not phone_list:
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