import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Cho phép tất cả domain
    allow_credentials=True,
    allow_methods=["*"],      # Cho phép GET, POST, PUT, DELETE...
    allow_headers=["*"],      # Cho phép tất cả headers
)

@app.get("/transactions/get_all_file")
def get_all_file():
    return {"message": "API đang chạy", "data": []}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="localhost", port=8000, reload=True)
