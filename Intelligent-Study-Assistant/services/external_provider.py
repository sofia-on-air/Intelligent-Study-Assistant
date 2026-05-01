from models.external_provider import ExternalProvider
from sqlalchemy.orm import Session
from dto import external_provider


def create(data: external_provider.External_provider, db: Session):
    external_provider = ExternalProvider(
        user_id=data.user_id,
        provider_name=data.provider_name,
        access_token=data.access_token,
        status=data.status
    )
    try:
        db.add(external_provider)
        db.commit()
        db.refresh(external_provider)
    except Exception as e:
        print(e)
    return external_provider


def get(id: int, db: Session):
    return db.query(ExternalProvider).filter(ExternalProvider.external_provider_id == id).first()


def update(data: external_provider.External_provider, db: Session, id: int):
    external_provider = db.query(ExternalProvider).filter(ExternalProvider.external_provider_id == id).first()
    if external_provider:
        external_provider.user_id = data.user_id
        external_provider.provider_name = data.provider_name
        external_provider.access_token = data.access_token
        external_provider.status = data.status
        db.commit()
        db.refresh(external_provider)
    return external_provider


def remove(db: Session, id: int):
    deleted = db.query(ExternalProvider).filter(ExternalProvider.external_provider_id == id).delete()
    if deleted:
        db.commit()
    return deleted