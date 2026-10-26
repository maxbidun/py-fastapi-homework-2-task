from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
import pycountry

from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas.movies import (
    MoviesListShema,
    MoviesCreateShema,
    MovieDetailShema,
    MoviesUpdateShema,
    MovieUpdateResponseSchema
)

router = APIRouter()


@router.get("/movies/", response_model=MoviesListShema)
async def get_movies(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=20),
):
    movies = (
        await db.scalars(
            select(MovieModel)
            .order_by(MovieModel.id.desc())
            .limit(per_page)
            .offset((page - 1) * per_page)
        )
    ).all()
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


@router.post("/movies/", response_model=MovieDetailShema, status_code=status.HTTP_201_CREATED)
async def create_movie(movie: MoviesCreateShema, db: AsyncSession = Depends(get_db)):
    movie_test = await db.scalar(
        select(MovieModel).where(
            MovieModel.name == movie.name,
            MovieModel.date == movie.date,
        )
    )

    if movie_test:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A movie with the name '{movie.name}' and release date "
                f"'{movie.date}' already exists."
            ),
        )

    country = await db.scalar(
        select(CountryModel).where(CountryModel.code == movie.country)
    )
    if country is None:
        country_info = pycountry.countries.get(alpha_3=movie.country) or pycountry.countries.get(alpha_2=movie.country)

        if country_info is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown country code: {movie.country}",
            )

        country = CountryModel(
            code=movie.country,
            name=country_info.name,
        )
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
        result = await db.execute(
            select(MovieModel)
            .options(
                joinedload(MovieModel.country),
                selectinload(MovieModel.genres),
                selectinload(MovieModel.actors),
                selectinload(MovieModel.languages),
            )
            .where(MovieModel.id == new_movie.id)
        )
        new_movie = result.unique().scalar_one()
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
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
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


@router.patch("/movies/{movie_id}/", response_model=MovieUpdateResponseSchema, status_code=status.HTTP_200_OK,)
async def update_movie(
    movie_id: int,
    movie_update: MoviesUpdateShema,
    db: AsyncSession = Depends(get_db),
):
    movie = await db.scalar(select(MovieModel).options(
        joinedload(MovieModel.country),
        selectinload(MovieModel.genres),
        selectinload(MovieModel.actors),
        selectinload(MovieModel.languages),
    ).where(MovieModel.id == movie_id))
    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie with the given ID was not found.")
    update_data = movie_update.model_dump(exclude_unset=True)
    new_name = update_data.get("name", movie.name)
    new_date = update_data.get("date", movie.date)

    duplicate_movie = await db.scalar(
        select(MovieModel).where(
            MovieModel.name == new_name,
            MovieModel.date == new_date,
            MovieModel.id != movie_id,
        )
    )

    if duplicate_movie is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A movie with the name '{new_name}' "
                f"and release date '{new_date}' already exists."
            ),
        )
    for field, value in update_data.items():
        setattr(movie, field, value)
    try:
        await db.commit()
        await db.refresh(movie)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="An error occurred while saving the movie.")
    return {"detail": "Movie updated successfully."}
