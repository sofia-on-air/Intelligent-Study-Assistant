from sqlalchemy import Column, Integer, String, Text, ForeignKey
from database import Base


class ExternalProvider(Base):
    __tablename__ = 'external_provider'

    external_provider_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    provider_name = Column(String)
    access_token = Column(Text)  
    refresh_token = Column(String, nullable=True)  
    status = Column(String)