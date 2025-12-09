from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Backend đang chạy ngon lành!", "service": "Log Analyzer API"}
@app.get("/api/test")
def test_connect():
    return {"message": "Kết nối thành công đến Log Analyzer API!"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
    
    