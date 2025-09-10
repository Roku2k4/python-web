from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.services.phone_import_service import *

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/get_phone")
def get_transactions(file_name: str, db: Session = Depends(get_db)):
    check = get_phone_check_info_by_filename(file_name)
    if check == "Not found":
        return  []
    else:
        return check

@router.get("/get_all_file")
def get_all_file(db: Session = Depends(get_db)):
    check = get_list_file()
    if (check == "Not found"):
        return  []
    else:
        return check


@router.post("/import")
def create_phone(request: dict, db: Session = Depends(get_db)):
    file_name = request.get("file_name")
    phone = request.get("phone")
    run_date = request.get("run_date")
    phone = import_jobs_from_csv(phone, file_name,run_date)
    return phone