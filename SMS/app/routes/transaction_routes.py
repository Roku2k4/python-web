from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.Transactions import Transaction
from app.services.phone_import_service import *

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/get_phone")
def get_transactions(request: dict,db: Session = Depends(get_db)):
    file_name = request.get("file_name")
    check = get_phone_check_info_by_filename(file_name)
    if(check == "Not found"):
        return dict(
            message="Not found",
            data = []
        )
    else:
        return dict(
            message="Found",
            data = check
        )

@router.get("/get_all_file")
def get_all_file(db: Session = Depends(get_db)):
    check = get_list_file()
    if (check == "Not found"):
        return dict(
            message="Not found",
            data=[]
        )
    else:
        return dict(
            message="Found",
            data=check
        )


@router.post("/")
def create_phone(request: dict, db: Session = Depends(get_db)):
    file_name = request.get("file_name")
    file_path = request.get("file_path")
    run_date = request.get("run_date")
    phone = import_jobs_from_csv(file_path, file_name,run_date)
    return dict(
        data = phone
    )

# @router.post("/update")
# def update_phone(request: dict, db: Session = Depends(get_db)):
#     session = SessionLocal()
#     sdt = request.get("sdt")
#     job_trans = session.query(Transaction.status, Transaction.transaction_date).filter(Transaction.phone == sdt).first()
#     if job_trans == None:
#         return "Not found"
#     job_check = session.query(PhoneCheckInfo).filter(PhoneCheckInfo.sdt == sdt).first()
#     if job_check == None:
#         return "Not found"
#     if job_trans.status == 1 and job_check.run_date <= job_trans.transaction_date <= job_check.run_date + timedelta(
#             days=34):
#         job_check.is_update = 1
#         session.commit()
#     return dict(
#         data = job_check.is_update
#     )