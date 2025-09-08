from copy import deepcopy
from typing import Annotated
from datetime import datetime

from fastapi import FastAPI, status, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
import uvicorn
import requests

from schemas import GameMetadata
from mongo_db_processor import MongoRepository
from scrapers.game_page_scraper import get_game_info
from scrapers.populate_db import top_games, top_games_metadata
from middleware import RequestLimiter

app = FastAPI()
repository = MongoRepository()

@app.get('/games', response_model=list[GameMetadata])
def get_games():
    return [GameMetadata(**game) for game in repository.find_games([{}])]

@app.post('/games/{appid}')
def add_game(appid: int):
    if repository.find_game({'id': appid}):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={'Msg': 'Current game already in the lib'}
        )
    try:
        game_to_add = get_game_info(appid).model_dump()

    except AttributeError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={'Msg': "A game with this id doesn't exist"}
        )

    repository.add_game(game_to_add)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={'Msg': f"Game {game_to_add['title']} has been added to the lib"}
    )

@app.get('/games/top_games')
def get_top_games(num_games: Annotated[int, Query(ge=1, le=99)]):
    games = top_games(num_games)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(games)
    )

@app.get('/games/top_games_info')
def get_top_games_info(num_games: Annotated[int, Query(ge=1, le=99)]):
    games = top_games_metadata(num_games)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(games)
    )


@app.get('/games/search', response_model=list[GameMetadata])
def search_games(appid: Annotated[int | None, Query(ge=1)] = None,
                 title: Annotated[str | None, Query()] = None,
                 description: Annotated[str | None, Query()] = None,
                 release_date: Annotated[datetime | None, Query()] = None,
                 developers: Annotated[list[str] | None, Query()] = None,
                 publishers: Annotated[list[str] | None, Query()] = None,
                 tags: Annotated[list[str] | None, Query()] = None,
                 features: Annotated[list[str] | None, Query()] = None,
                 edition_min: Annotated[int | None, Query(ge=0)] = None,
                 edition_max: Annotated[int | None, Query(ge=0)] = None):

    if not any([appid, title, description, release_date, developers, publishers, tags, edition_min, edition_max, features]):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={'msg': "Can't search for nothin'"}
        )

    params = []
    if appid:
        params.append({'appid': appid})
    if title:
        params.append({'title': {'$regex': title, '$options': 'i'}})
    if description:
        params.append({'description': {'$regex': description, '$options': 'i'}})
    if release_date:
        params.append({'release_date': release_date})
    if developers:
        params.append({'developers.developer': {'$in': developers}})
    if publishers:
        params.append({'developers.publisher': {'$in': publishers}})
    if tags:
        params.append({'tags': {'$in': tags}})
    if features:
        params.append({'features': {'$in': features}})
    
    price_search = None
    if any([edition_min, edition_max]):
        price_search = {}
        if edition_min:
            price_search['$gte'] = edition_min
        if edition_max:
            price_search['$lte'] = edition_max

    return [GameMetadata(**games) for games in repository.find_games(params, price_search=price_search)]


@app.get('/games/applist', include_in_schema=False)
def get_appids():

    response = requests.get('https://api.steampowered.com/ISteamApps/GetAppList/v2', timeout=10)
    applist = response.json()['applist']['apps']
    repository.insert_applist(deepcopy(applist))
    return applist


app.add_middleware(RequestLimiter)


if __name__ == '__main__':
    uvicorn.run(app)
