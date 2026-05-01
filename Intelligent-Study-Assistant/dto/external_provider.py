from pydantic import BaseModel

class External_provider(BaseModel):
    user_id: int
    provider_name: str
    access_token: str
    status: str