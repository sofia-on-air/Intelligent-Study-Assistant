from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db

from services import external_provider as ExternalProviderService
from dto import external_provider as ExternalProviderDTO

router = APIRouter()

@router.post('/')
async def create(data: ExternalProviderDTO.External_provider, db: Session = Depends(get_db)):
    return ExternalProviderService.create(data, db)

@router.get('/{id}')
async def get(id: int, db: Session = Depends(get_db)):
    return ExternalProviderService.get(id, db)

@router.put('/{id}')
async def update(id: int, data: ExternalProviderDTO.External_provider, db: Session = Depends(get_db)):
    return ExternalProviderService.update(data, db, id)

@router.delete('/{id}')
async def delete(id: int, db: Session = Depends(get_db)):
    return ExternalProviderService.remove(db, id)
