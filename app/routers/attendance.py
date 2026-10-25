from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
import math

from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_user

router = APIRouter(
    prefix="/attendance",
    tags=["Attendance"]
)

@router.post("/{course_id}", response_model=schemas.AttendanceResponse)
def mark_attendance(
    course_id: int,
    attendance: schemas.AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 1. Verify the course belongs to the user
    course = db.query(models.Course).filter(
        models.Course.id == course_id,
        models.Course.user_id == current_user.id
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # 2. Check if an attendance record for this date already exists
    existing_record = db.query(models.AttendanceRecord).filter(
        models.AttendanceRecord.course_id == course_id,
        models.AttendanceRecord.date == attendance.date
    ).first()

    if existing_record:
        # Update existing record to handle the unique (course, date) constraint gracefully
        existing_record.status = attendance.status
        db.commit()
        db.refresh(existing_record)
        return existing_record
    else:
        # Create new record
        new_record = models.AttendanceRecord(
            **attendance.dict(),
            course_id=course_id
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        return new_record


@router.get("/{course_id}/status")
def get_attendance_status(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 1. Verify ownership
    course = db.query(models.Course).filter(
        models.Course.id == course_id,
        models.Course.user_id == current_user.id
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # 2. Tally the records
    # Note: 'cancelled' classes usually don't count toward the denominator.
    records = db.query(
        models.AttendanceRecord.status, 
        func.count(models.AttendanceRecord.id)
    ).filter(
        models.AttendanceRecord.course_id == course_id,
        models.AttendanceRecord.status.in_(["present", "absent"])
    ).group_by(models.AttendanceRecord.status).all()

    # Convert query results to a dictionary like {"present": 10, "absent": 2}
    counts = dict(records)
    p = counts.get("present", 0)
    a = counts.get("absent", 0)
    total_classes = p + a

    if total_classes == 0:
        return {
            "course_name": course.name,
            "attendance_percentage": 0.0,
            "status_message": "No valid attendance data yet.",
            "safe_leaves": 0,
            "classes_needed": 0
        }

    current_percentage = (p / total_classes) * 100

    # 3. The Math for 75% Risk Calculation
    # We want: P / (P + A + x) >= 0.75  =>  x <= (P - 3A) / 3
    # If short, we need y classes: (P + y) / (P + A + y) >= 0.75  =>  y >= 3A - P
    
    margin = p - (3 * a)
    
    if margin >= 0:
        safe_leaves = math.floor(margin / 3)
        classes_needed = 0
        message = f"You are safe! You can skip {safe_leaves} more classes and stay at or above 75%."
    else:
        safe_leaves = 0
        classes_needed = (3 * a) - p
        message = f"Warning: You are below 75%. You need to attend the next {classes_needed} classes without missing any."

    return {
        "course_name": course.name,
        "total_attended": p,
        "total_missed": a,
        "attendance_percentage": round(current_percentage, 2),
        "safe_leaves": safe_leaves,
        "classes_needed": classes_needed,
        "status_message": message
    }