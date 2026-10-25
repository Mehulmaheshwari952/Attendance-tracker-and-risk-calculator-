from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas
from app.database import get_db
# Adjust this import based on where you put the get_current_user function
from app.dependencies import get_current_user 

router = APIRouter(
    prefix="/courses",
    tags=["Courses"]
)

@router.post("/", response_model=schemas.CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    course: schemas.CourseCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    # Ensure a user doesn't create duplicate course names for themselves
    existing_course = db.query(models.Course).filter(
        models.Course.name == course.name,
        models.Course.user_id == current_user.id
    ).first()
    
    if existing_course:
        raise HTTPException(status_code=400, detail="Course already exists for this user")

    new_course = models.Course(**course.dict(), user_id=current_user.id)
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course

@router.get("/", response_model=List[schemas.CourseResponse])
def get_courses(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    courses = db.query(models.Course).filter(models.Course.user_id == current_user.id).all()
    return courses

@router.get("/{course_id}", response_model=schemas.CourseResponse)
def get_course(
    course_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    course = db.query(models.Course).filter(
        models.Course.id == course_id, 
        models.Course.user_id == current_user.id
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    course_query = db.query(models.Course).filter(
        models.Course.id == course_id, 
        models.Course.user_id == current_user.id
    )
    
    if not course_query.first():
        raise HTTPException(status_code=404, detail="Course not found")
        
    course_query.delete(synchronize_session=False)
    db.commit()
    return {"message": "Course deleted successfully"}