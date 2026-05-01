from models.user import User
from sqlalchemy.orm import Session
from dto import user
import bcrypt 

def create_user(data: user.User, db: Session):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        return None
    
    hashed_password = bcrypt.hashpw(
        data.password_hash.encode('utf-8'), 
        bcrypt.gensalt()
    )
    new_user = User(
        email=data.email, 
        password_hash=hashed_password.decode('utf-8')
    )
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception as e:
        print(e)
    return new_user


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def update(data: user.User, db: Session, id: int):
    existing_user = db.query(User).filter(User.user_id == id).first()
    if existing_user:
        existing_user.email = data.email
        existing_user.password_hash = data.password_hash
        db.commit()
        db.refresh(existing_user)
    return existing_user

def remove(db: Session, id: int):
    deleted_user = db.query(User).filter(User.user_id == id).delete()
    if deleted_user:
        db.commit()
    return deleted_user