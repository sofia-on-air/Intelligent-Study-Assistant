from sqlalchemy import Column, Integer, Text, ForeignKey
from database import Base

class Flashcard(Base):
    __tablename__ = 'flashcards'

    card_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    front_text = Column(Text)
    back_text = Column(Text)