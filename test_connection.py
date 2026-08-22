from app.database import engine, Base
from app.models import User, Course, ClassSchedule, AttendanceRecord

Base.metadata.create_all(bind=engine)
print("Database connection successful and tables created.")