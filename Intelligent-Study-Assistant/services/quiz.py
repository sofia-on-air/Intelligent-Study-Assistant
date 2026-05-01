from models.quiz import Quiz
from sqlalchemy.orm import Session
from dto import quiz


def create(data: quiz.Quiz, db: Session):
    quiz = Quiz(
        user_id=data.user_id,
        quiz_data_json=data.quiz_data_json,
        score=data.score
    )
    try:
        db.add(quiz)
        db.commit()
        db.refresh(quiz)
    except Exception as e:
        print(e)
    return quiz


def get(id: int, db: Session):
    return db.query(Quiz).filter(Quiz.quiz_id == id).first()


def update(data: quiz.Quiz, db: Session, id: int):
    quiz = db.query(Quiz).filter(Quiz.quiz_id == id).first()
    if quiz:
        quiz.user_id = data.user_id
        quiz.quiz_data_json = data.quiz_data_json
        quiz.score = data.score
        db.commit()
        db.refresh(quiz)
    return quiz


def remove(db: Session, id: int):
    deleted = db.query(Quiz).filter(Quiz.quiz_id == id).delete()
    if deleted:
        db.commit()
    return deleted
