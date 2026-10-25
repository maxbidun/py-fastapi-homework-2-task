# Write your code here
from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import date as date_type, timedelta


class CountrySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int  # noqa: VNE003
    code: str
    name: str | None


class GenreSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int  # noqa: VNE003
    name: str


class ActorSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int  # noqa: VNE003
    name: str


class LanguageSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int  # noqa: VNE003
    name: str


class MovieDetailShema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int  # noqa: VNE003
    name: str = Field(..., max_length=255)
    date: date_type
    score: float = Field(..., ge=0, le=100)
    overview: str
    status: str
    budget: float = Field(..., ge=0)
    revenue: float = Field(..., ge=0)
    country: CountrySchema
    genres: list[GenreSchema]
    actors: list[ActorSchema]
    languages: list[LanguageSchema]

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: date_type) -> date_type:
        today = date_type.today()
        max_date = today + timedelta(days=365)
        if value > max_date:
            raise ValueError("Date must be in the future")
        return value


class MovieListItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int  # noqa: VNE003
    name: str
    date: date_type
    score: float
    overview: str


class MoviesListShema(BaseModel):
    movies: List[MovieListItemSchema]
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
    country: str = Field(pattern=r"^[A-Z]{3}$")
    genres: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class MoviesUpdateShema(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    date: date_type | None = None
    score: float | None = Field(default=None, ge=0, le=100)
    overview: str | None = None
    status: str | None = None
    budget: float | None = Field(default=None, ge=0)
    revenue: float | None = Field(default=None, ge=0)


class MovieUpdateResponseSchema(BaseModel):
    detail: str
