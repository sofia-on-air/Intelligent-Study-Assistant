from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db

from services import quiz as QuizService
from dto import quiz as QuizDTO

router = APIRouter()

@router.post('/')
async def create(data: QuizDTO.Quiz, db: Session = Depends(get_db)):
    return QuizService.create(data, db)

@router.get('/{id}')
async def get(id: int, db: Session = Depends(get_db)):
    return QuizService.get(id, db)

@router.put('/{id}')
async def update(id: int, data: QuizDTO.Quiz, db: Session = Depends(get_db)):
    return QuizService.update(data, db, id)

@router.delete('/{id}')
async def delete(id: int, db: Session = Depends(get_db)):
    return QuizService.remove(db, id)
