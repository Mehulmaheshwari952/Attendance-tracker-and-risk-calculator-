from fastapi import FastAPI
import uvicorn
from .routers import auth,courses,attendance
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Attendance Tracker API")
app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(attendance.router)

@app.get("/")
def read_root():
    return {"Hello": "World"}

Instrumentator().instrument(app).expose(app)