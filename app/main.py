from fastapi import FastAPI
import uvicorn
from .routers import auth,courses,attendance

app = FastAPI()

app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(attendance.router)

@app.get("/")
def read_root():
    return {"Hello": "World"}
