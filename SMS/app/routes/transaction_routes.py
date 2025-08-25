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
        message="success",
        data = phone
    )

