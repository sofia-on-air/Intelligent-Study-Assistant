from pydantic import BaseModel

class Flashcard(BaseModel):
    user_id: int
    front_text: str
    back_text: str