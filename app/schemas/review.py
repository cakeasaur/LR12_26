from typing import Optional
from pydantic import BaseModel, field_validator


class ReviewCreate(BaseModel):
    apartment_id: int
    rating: int
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def rating_in_range(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("Рейтинг должен быть от 1 до 5")
        return v


class ReviewRead(BaseModel):
    id: int
    apartment_id: int
    author_id: int
    rating: int
    comment: Optional[str]

    model_config = {"from_attributes": True}
