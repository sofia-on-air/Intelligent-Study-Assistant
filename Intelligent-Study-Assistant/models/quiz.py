from sqlalchemy import Column, Integer, String, Text, ForeignKey
from database import Base


class Quiz(Base):
    __tablename__ = 'quizzes'

    quiz_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    quiz_data_json = Column(Text)
    score = Column(Integer)
    topic = Column(String, nullable=True)