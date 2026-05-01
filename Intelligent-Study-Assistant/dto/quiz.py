from pydantic import BaseModel

class Quiz(BaseModel):
    user_id: int
    quiz_data_json: str
    score: int