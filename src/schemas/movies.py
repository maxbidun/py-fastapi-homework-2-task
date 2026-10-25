# Write your code here
from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import date as date_type, timedelta


class MovieDetailShema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str = Field(..., max_length=255)
    date: date_type
    score: float = Field(..., ge=0, le=100)
    overview: str
    status: str
    budget: float = Field(..., ge=0)
    revenue: float = Field(..., ge=0)
    country_id: int
    country_name: str
    genre: str
    actors: list
    languages: list

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: date_type) -> date_type:
        today = date_type.today()
        max_date = today + timedelta(days=365)
        if value > max_date:
            raise ValueError("Date must be in the future")
        return value

class MoviesListShema(BaseModel):
    movies: List[MovieDetailShema]
    prev_page: str | None
    next_page: str | None
    total_pages: int
    total_items: int


class MoviesCreateShema(BaseModel):
    name: str = Field(..., max_length=255)
    date: date_type
    score: float = Field(..., ge=0, le=100)
    overview: str
    status: str
    budget: float = Field(..., ge=0)
    revenue: float = Field(..., ge=0)
    country_id: int


class MoviesUpdateShema(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    date: date_type | None = None
    score: float | None = Field(default=None, ge=0, le=100)
    overview: str | None = None
    status: str | None = None
    budget: float | None = Field(default=None, ge=0)
    revenue: float | None = Field(default=None, ge=0)