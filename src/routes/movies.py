from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.util import await_

from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas.movies import MoviesListShema, MoviesCreateShema, MovieDetailShema, MoviesUpdateShema

router = APIRouter()

# Write your code here
@router.get("/movies/", response_model=list[MovieDetailShema])
async def get_movies(db: AsyncSession = Depends(get_db), page: int = Query(1, ge=1), per_page: int = Query(10, ge=1, le=20)):
    movies = list(await db.scalars(select(MovieModel).limit(per_page).offset((page-1) * per_page))).all()
    total_items = await db.scalar(select(func.count()).select_from(MovieModel))

    if total_items % per_page != 0:
        total_pages = total_items // per_page + 1
    else:
        total_pages = total_items // per_page

    prev_page = None
    next_page = None

    if page > 1:
        prev_page = f"/theater/movies/?page={page - 1}&per_page={per_page}"
    if total_pages > page:
        next_page = f"/theater/movies/?page={page + 1}&per_page={per_page}"

    if not movies:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No movies found.")
    return MoviesListShema(
        movies=movies,
        prev_page=prev_page,
        next_page=next_page,
        total_pages=total_pages,
        total_items=total_items
    )

@router.post("/movies/", response_model=MovieDetailShema)
async def create_movie(movie: MoviesCreateShema, db: AsyncSession = Depends(get_db), status_code=status.HTTP_201_CREATED):
    movie_test = await db.scalar(
        select(MovieModel).where(
            MovieModel.name == movie.name,
            MovieModel.date == movie.date,
        )
    )

    if movie_test:
        raise HTTPException(status_code=400, detail=f"A movie with the name '{movie.name}' and release date '{movie.date}' already exists.")

    movie = MovieModel(**movie.model_dump())
    db.add(movie)
    try:
        await db.commit()
        await db.refresh(movie)
    except:
        await db.rollback()
        raise HTTPException(status_code=400, detail="An error occurred while saving the movie.")
    return movie


@router.get("/movies/{movie_id}/", response_model=MovieDetailShema)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await db.scalar(select(MovieModel).where(MovieModel.id == movie_id))

    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie with the given ID was not found.")
    return movie


@router.delete("/movies/{movie_id}/", response_model=MovieDetailShema)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db), status_code=status.HTTP_204_NO_CONTENT):
    movie = await db.scalar(select(MovieModel).where(MovieModel.id == movie_id))
    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie with the given ID was not found.")
    await db.delete(movie)
    await db.commit()
    return movie

@router.patch("/movies/{movie_id}/", response_model=MovieDetailShema)
async def update_movie(movie_id: int, movie_update: MoviesUpdateShema, db:  AsyncSession = Depends(get_db)):
    movie = await db.scalar(select(MovieModel).where(MovieModel.id == movie_id))
    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie with the given ID was not found.")
    update_data = movie_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(movie, field, value)
    try:
        await db.commit()
        await db.refresh(movie)
    except:
        await db.rollback()
        raise HTTPException(status_code=400, detail="An error occurred while saving the movie.")
    return {"detail": "Movie updated successfully."}
