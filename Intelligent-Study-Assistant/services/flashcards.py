from models.flashcards import Flashcard
from sqlalchemy.orm import Session
from dto import flashcards


def create(data: flashcards.Flashcard, db: Session):
    card = Flashcard(
        user_id=data.user_id,
        front_text=data.front_text,
        back_text=data.back_text
    )
    try:
        db.add(card)
        db.commit()
        db.refresh(card)
    except Exception as e:
        print(e)
    return card


def get(id: int, db: Session):
    return db.query(Flashcard).filter(Flashcard.card_id == id).first()


def update(data: flashcards.Flashcard, db: Session, id: int):
    card = db.query(Flashcard).filter(Flashcard.card_id == id).first()
    if card:
        card.user_id = data.user_id
        card.front_text = data.front_text
        card.back_text = data.back_text
        db.commit()
        db.refresh(card)
    return card


def remove(db: Session, id: int):
    deleted = db.query(Flashcard).filter(Flashcard.card_id == id).delete()
    if deleted:
        db.commit()
    return deleted
