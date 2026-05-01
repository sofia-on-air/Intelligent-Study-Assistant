from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db

from services import flashcards as FlashcardsService
from dto import flashcards as FlashcardsDTO

router = APIRouter()

@router.post('/')
async def create(data: FlashcardsDTO.Flashcard, db: Session = Depends(get_db)):
    return FlashcardsService.create(data, db)

@router.get('/{id}')
async def get(id: int, db: Session = Depends(get_db)):
    return FlashcardsService.get(id, db)

@router.put('/{id}')
async def update(id: int, data: FlashcardsDTO.Flashcard, db: Session = Depends(get_db)):
    return FlashcardsService.update(data, db, id)

@router.delete('/{id}')
async def delete(id: int, db: Session = Depends(get_db)):
    return FlashcardsService.remove(db, id)
