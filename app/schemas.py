
from datetime import date as Date
from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    email: str
    password: str
    term_start_date: Date
    term_end_date: Date

class UserResponse(BaseModel):
    id: int
    email: str
    term_start_date: Date
    term_end_date: Date

    class Config:
        from_attributes = True

class CourseCreate(BaseModel):
    name: str
    min_attendance_pct: float

class CourseResponse(BaseModel):
    id: int
    name: str
    min_attendance_pct: float = 75.0

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: str
    password: str

class AttendanceCreate(BaseModel):
    date: Date
    status: str # "present", "absent", or "cancelled"

class AttendanceResponse(BaseModel):
    id: int
    course_id: int
    date: Date = Field(validation_alias="date_")
    status: str

    class Config:
        from_attributes = True
    