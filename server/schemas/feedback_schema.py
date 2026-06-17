from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class FeedbackType(str, Enum):
    bug = "Bug"
    content_error = "Content Error"
    feature_request = "Feature Request"
    general = "General"

class FeedbackCreate(BaseModel):
    type: FeedbackType
    description: str = Field(..., min_length=5, max_length=1000)
    url: str = Field(default="")

class FeedbackDocument(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    type: FeedbackType
    description: str
    url: str
    created_at: datetime
