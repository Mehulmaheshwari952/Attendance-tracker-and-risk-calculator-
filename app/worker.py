import os
from celery import Celery
from celery.schedules import crontab
from sqlalchemy.orm import Session
from sqlalchemy import func

from app import models
from app.database import SessionLocal

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery using Redis as both the broker and result backend
celery_app = Celery(
    "attendance_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Configure Celery Beat to run the risk check job daily at midnight
celery_app.conf.beat_schedule = {
    'daily-risk-notification': {
        'task': 'app.worker.check_attendance_risk',
        'schedule': crontab(hour=0, minute=0), 
    },
}
celery_app.conf.timezone = 'UTC'

@celery_app.task
def check_attendance_risk():
    """
    Background job to find users below 75% attendance and simulate sending a notification.
    """
    db: Session = SessionLocal()
    try:
        # Group attendance by course and status
        records = db.query(
            models.AttendanceRecord.course_id,
            models.AttendanceRecord.status,
            func.count(models.AttendanceRecord.id).label('count')
        ).filter(
            models.AttendanceRecord.status.in_(["present", "absent"])
        ).group_by(
            models.AttendanceRecord.course_id, 
            models.AttendanceRecord.status
        ).all()

        # Process the results to calculate percentages per course
        course_stats = {}
        for course_id, status, count in records:
            if course_id not in course_stats:
                course_stats[course_id] = {"present": 0, "absent": 0}
            course_stats[course_id][status] = count

        # Identify at-risk courses
        for course_id, stats in course_stats.items():
            p = stats["present"]
            a = stats["absent"]
            total = p + a
            
            if total > 0:
                percentage = (p / total) * 100
                if percentage < 75.0:
                    # In a production app, you would query the user's email here and send via AWS SES / SendGrid
                    print(f"⚠️ ASYNC NOTIFICATION: Course {course_id} is at risk! Current attendance: {percentage:.2f}%")
                    
        return "Daily risk check completed successfully."
    finally:
        db.close()