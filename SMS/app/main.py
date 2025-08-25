from fastapi import FastAPI
from app.routes import transaction_routes
from app.database import Base, engine

# Tạo bảng trong DB
Base.metadata.create_all(bind=engine)

app = FastAPI(title="My Python Web App")

# Đăng ký route
app.include_router(transaction_routes.router, prefix="/transactions", tags=["Transactions"])
