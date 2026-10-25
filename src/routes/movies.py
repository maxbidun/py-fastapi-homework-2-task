from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.util import await_

from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas.movies import MoviesListShema, MoviesCreateShema, MovieDetailShema, MoviesUpdateShema

router = APIRouter()

# Write your code here
@router.get("/movies/", response_model=MoviesListShema)
async def get_movies(db: AsyncSession = Depends(get_db), page: int = Query(1, ge=1), per_page: int = Query(10, ge=1, le=20)):
    movies = list(await db.scalars(select(MovieModel).order_by(MovieModel.id.desc()).limit(per_page).offset((page-1) * per_page))).all()
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

@router.post("/movies/", response_model=MoviesListShema, status_code=status.HTTP_201_CREATED)
async def create_movie(movie: MoviesCreateShema, db: AsyncSession = Depends(get_db)):
    movie_test = await db.scalar(
        select(MovieModel).where(
            MovieModel.name == movie.name,
            MovieModel.date == movie.date,
        )
    )

    if movie_test:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"A movie with the name '{movie.name}' and release date '{movie.date}' already exists.")

    country = await db.scalar(
        select(CountryModel).where(CountryModel.code == movie.country)
    )
    if country is None:
        country = CountryModel(code=movie.country, name=movie.country)
        db.add(country)
        await db.flush()

    async def get_or_create(model, name: str):
        entity = await db.scalar(select(model).where(model.name == name))
        if entity is None:
            entity = model(name=name)
            db.add(entity)
            await db.flush()
        return entity

    movie_data = movie.model_dump(exclude={"country", "genres", "actors", "languages"})
    new_movie = MovieModel(
        **movie_data,
        country=country,
        genres=[await get_or_create(GenreModel, name) for name in movie.genres],
        actors=[await get_or_create(ActorModel, name) for name in movie.actors],
        languages=[await get_or_create(LanguageModel, name) for name in movie.languages],
    )
    db.add(new_movie)
    try:
        await db.commit()
        await db.refresh(new_movie)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="A movie with this name and release date already exists.")
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="An error occurred while saving the movie.")
    return new_movie


@router.get("/movies/{movie_id}/", response_model=MovieDetailShema)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await db.scalar(select(MovieModel) .options(
        joinedload(MovieModel.country),
        selectinload(MovieModel.genres),
        selectinload(MovieModel.actors),
        selectinload(MovieModel.languages),
    ).where(MovieModel.id == movie_id))

    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie with the given ID was not found.")
    return movie


@router.delete("/movies/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db), status_code=status.HTTP_204_NO_CONTENT):
    movie = await db.scalar(select(MovieModel) .options(
        joinedload(MovieModel.country),
        selectinload(MovieModel.genres),
        selectinload(MovieModel.actors),
        selectinload(MovieModel.languages),
    ).where(MovieModel.id == movie_id))
    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie with the given ID was not found.")
    await db.delete(movie)
    await db.commit()


@router.patch("/movies/{movie_id}/", response_model=MoviesUpdateShema, status_code=status.HTTP_200_OK,)
async def update_movie(movie_id: int, movie_update: MoviesUpdateShema, db:  AsyncSession = Depends(get_db)):
    movie = await db.scalar(select(MovieModel).options(
        joinedload(MovieModel.country),
        selectinload(MovieModel.genres),
        selectinload(MovieModel.actors),
        selectinload(MovieModel.languages),
    ).where(MovieModel.id == movie_id))
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
