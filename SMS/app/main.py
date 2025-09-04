from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import check_phone_routes
from app.database import Base, engine
from apscheduler.schedulers.background import BackgroundScheduler
from app.utils.worker import schedule_jobs
from contextlib import asynccontextmanager

# Tạo bảng trong DB
Base.metadata.create_all(bind=engine)
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    scheduler.start()
    schedule_jobs(scheduler)
    print("Scheduler started!")

    yield  # >>> tại đây FastAPI sẽ xử lý API bình thường, không block

    # --- Shutdown ---
    scheduler.shutdown()
    print("Scheduler stopped!")
app = FastAPI(title="My Python Web App", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # domain frontend được phép gọi
    allow_credentials=True,
    allow_methods=["*"],   # cho phép tất cả method: GET, POST, PUT, DELETE...
    allow_headers=["*"],   # cho phép tất cả headers
)

# Đăng ký route
app.include_router(check_phone_routes.router, prefix="/transactions", tags=["Transactions"])

