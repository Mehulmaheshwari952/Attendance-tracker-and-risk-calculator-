from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
import math
import json

from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_user
from app.redis import redis_client # Import the new redis client

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
    course = db.query(models.Course).filter(
        models.Course.id == course_id,
        models.Course.user_id == current_user.id
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    existing_record = db.query(models.AttendanceRecord).filter(
        models.AttendanceRecord.course_id == course_id,
        models.AttendanceRecord.date == attendance.date
    ).first()

    if existing_record:
        existing_record.status = attendance.status
        db.commit()
        db.refresh(existing_record)
        record = existing_record
    else:
        new_record = models.AttendanceRecord(
            **attendance.dict(),
            course_id=course_id
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        record = new_record

    # --- CACHE INVALIDATION ---
    # Clear the cached status so the next GET request forces a recalculation
    cache_key = f"attendance_status:{current_user.id}:{course_id}"
    redis_client.delete(cache_key)

    return record


@router.get("/{course_id}/status")
def get_attendance_status(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # --- CACHE READ ---
    cache_key = f"attendance_status:{current_user.id}:{course_id}"
    cached_data = redis_client.get(cache_key)
    
    if cached_data:
        # Return the cached JSON string as a Python dictionary
        return json.loads(cached_data)

    # 1. Verify ownership (if cache misses)
    course = db.query(models.Course).filter(
        models.Course.id == course_id,
        models.Course.user_id == current_user.id
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # 2. Tally the records
    records = db.query(
        models.AttendanceRecord.status, 
        func.count(models.AttendanceRecord.id)
    ).filter(
        models.AttendanceRecord.course_id == course_id,
        models.AttendanceRecord.status.in_(["present", "absent"])
    ).group_by(models.AttendanceRecord.status).all()

    counts = dict(records)
    p = counts.get("present", 0)
    a = counts.get("absent", 0)
    total_classes = p + a

    if total_classes == 0:
        result = {
            "course_name": course.name,
            "attendance_percentage": 0.0,
            "status_message": "No valid attendance data yet.",
            "safe_leaves": 0,
            "classes_needed": 0
        }
        # Cache this empty state briefly (e.g., 5 minutes)
        redis_client.set(cache_key, json.dumps(result), ex=300)
        return result

    current_percentage = (p / total_classes) * 100
    margin = p - (3 * a)
    
    if margin >= 0:
        safe_leaves = math.floor(margin / 3)
        classes_needed = 0
        message = f"You are safe! You can skip {safe_leaves} more classes and stay at or above 75%."
    else:
        safe_leaves = 0
        classes_needed = (3 * a) - p
        message = f"Warning: You are below 75%. You need to attend the next {classes_needed} classes without missing any."

    result = {
        "course_name": course.name,
        "total_attended": p,
        "total_missed": a,
        "attendance_percentage": round(current_percentage, 2),
        "safe_leaves": safe_leaves,
        "classes_needed": classes_needed,
        "status_message": message
    }

    # --- CACHE WRITE ---
    # Store the calculated result in Redis with a Time-To-Live (TTL) of 1 hour (3600 seconds)
    redis_client.set(cache_key, json.dumps(result), ex=3600)

    return result