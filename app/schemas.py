
from datetime import date
from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    password: str
    term_start_date: date
    term_end_date: date 

class UserResponse(BaseModel):
    id: int
    email: str
    term_start_date: date
    term_end_date: date

    class Config:
        from_attributes = True

class CourseCreate(BaseModel):
    name: str
    min_attendance_pct: float

class CourseResponse(BaseModel):
    id: int
    name: str
    min_attendance_pct: float = 75.0
    classes_held: int
    classes_attended: int
    current_pct: float
    safe_leaves_remaining: int  

class LoginRequest(BaseModel):
    email: str
    password: str

    