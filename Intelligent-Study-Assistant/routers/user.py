from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db

from services import user as UserService
from dto import user as UserDTO
import bcrypt 

router = APIRouter()

@router.post('/register', tags=["user"])
async def create(data: UserDTO.User, db: Session = Depends(get_db)):
    user = UserService.create_user(data, db)
    if user is None:
        return {"status": "error", "message": "User with this email already exists"}
    return {"status": "success"}

@router.post('/login')
async def login(data: UserDTO.User, db: Session = Depends(get_db)):
    existing_user = UserService.get_user_by_email(db, email=data.email)
    
    if not existing_user:
        return {
            "status": "error",
            "message": "Invalid email or password"
        }
    
    password_is_correct = bcrypt.checkpw(
        data.password_hash.encode('utf-8'),
        existing_user.password_hash.encode('utf-8')
    )
    
    if not password_is_correct:
        return {
            "status": "error",
            "message": "Invalid email or password"
        }
    
    return {
        "status": "success", 
        "user_id": existing_user.user_id
    }

@router.get('/{id}', tags=["user"])
async def get(id: int, db: Session = Depends(get_db)):
    return UserService.get_user(id, db)

@router.put('/{id}', tags=["user"])
async def update(id: int , data: UserDTO.User, db: Session = Depends(get_db)):
    return UserService.update(data, db, id)

@router.delete('/{id}', tags=["user"])
async def delete(id: int, db: Session = Depends(get_db)):
    return UserService.remove(db, id)