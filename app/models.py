
from sqlalchemy import SMALLINT, CheckConstraint, Column, ForeignKey, Integer, Numeric, String, DateTime, Date, Boolean, UniqueConstraint
from sqlalchemy.sql import func
from .database import Base
    
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    term_start_date = Column(Date, nullable=False)
    term_end_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    min_attendance_pct = Column(Numeric(5, 2), nullable=False, server_default="75.00")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

class ClassSchedule(Base):
    __tablename__ = "class_schedules"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(SMALLINT, nullable=False)  # e.g., 1 for Monday, 2 for Tuesday, etc.
    is_active = Column(Boolean, nullable=False, server_default="true")  # True for active, False for inactive
    __table_args__ = (CheckConstraint("day_of_week BETWEEN 0 AND 6"),)  # Ensure one schedule per course per day

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    date_ = Column(Date, nullable=False)
    status = Column(String(10), nullable=False)  # 'present' or 'absent'
    marked_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (UniqueConstraint('course_id', 'date_'), CheckConstraint("status IN ('present', 'absent', 'cancelled')"))  # Ensure one record per course per date