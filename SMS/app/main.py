from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import check_phone_routes
from app.database import Base, engine

# Tạo bảng trong DB
Base.metadata.create_all(bind=engine)

app = FastAPI(title="My Python Web App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # domain frontend được phép gọi
    allow_credentials=True,
    allow_methods=["*"],   # cho phép tất cả method: GET, POST, PUT, DELETE...
    allow_headers=["*"],   # cho phép tất cả headers
)

# Đăng ký route
app.include_router(check_phone_routes.router, prefix="/transactions", tags=["Transactions"])
