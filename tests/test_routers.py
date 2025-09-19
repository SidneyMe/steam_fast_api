from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from main import app, repository
from schemas import Game, GameMetadata
from middleware import RequestLimiter


client = TestClient(app)

def test_get_games():
    response = client.get('/games')
    assert response.status_code == 200
    assert response.json()[0].keys() == GameMetadata.model_fields.keys()


def test_add_existing_game():
    appid = 570 # dota 2 id

    repository.delete_game(appid)
    response = client.post(f'/games/{appid}')

    assert response.status_code == 201
    assert response.json() == {'Msg': "Game Dota 2 has been added to the lib"}

    repository.delete_game(appid)

def test_add_nonexisting_game():
    appid = 0

    response = client.post(f'/games/{appid}')

    assert response.status_code == 404
    assert "id doesn't exist" in response.json()['Msg']

def test_add_duplicated_game():
    mongo = repository.find_first_game()
    game = GameMetadata(**mongo)

    response = client.post(f'/games/{game.appid}')

    assert response.status_code == 409
    assert 'already in the lib' in response.json()['Msg']

def test_get_top_games():
    response = client.get('/games/top_games', params={'num_games': 10})

    assert response.status_code == 200
    assert len(response.json()) == 10

def test_get_top_games_info():
    response = client.get('/games/top_games_info', params={'num_games': 10})

    assert response.status_code == 200
    assert len(response.json()) == 10

def test_empty_search():
    response = client.get('/games/search')

    assert response.status_code == 400
    assert "search for nothin" in response.json()['msg']

@pytest.mark.parametrize(
    'param', ({'appid': 730},
              {'title': 'strike'},
              {'description': 'strike'},
              {'release_date': '2012-08-21T00:00:00.000Z'},
              {'developers': ['Valve']},
              {'publishers': ['Valve']},
              {'tags': ['FPS']},
              {'features': ['Stats']},
              {'edition_min': 10},
              {'edition_max': 30})
)
def test_valid_search_one_param(param):
    target_app_id = 730

    response = client.get('/games/search', params=param)
    appids = [game['appid'] for game in response.json()]

    assert target_app_id in appids

@pytest.mark.parametrize(
    'params',
    [
        ({'appid': 730, 'title': 'Counter'}),
        ({'title': 'strike', 'tags': ['FPS']}),
        ({'developers': ['Valve'], 'publishers': ['Valve']}),
        ({'tags': ['FPS', 'Shooter'], 'features': ['Stats']}),
        ({'edition_min': 0, 'edition_max': 20}),
        ({'description': 'Counter', 'release_date': '2012-08-21T00:00:00.000Z'}),
        ({'appid': 730, 'tags': ['FPS'], 'features': ['Stats'], 'edition_min': 0})
    ]
)
def test_valid_search_multiple_params(params):
    target_app_id = 730

    response = client.get('/games/search', params=params)
    appids = [game['appid'] for game in response.json()]

    assert response.status_code == 200
    assert target_app_id in appids

def test_search_no_results():
    response = client.get('/games/search', params={'title': 'test'})

    assert response.status_code == 200
    assert response.json() == []

def test_search_invalid_appid():
    response = client.get('/games/search', params={'appid': 0})

    assert response.status_code == 422

def test_search_invalid_edition_range():
    response = client.get('/games/search', params={'edition_min': -1})

    assert response.status_code == 422

def test_app_list():
    response = client.get('/games/applist')

    assert response.status_code == 200
    assert len(response.json()) > 200_000

#Yes, i'm aware that middleware is going to block any future tests after overwhelming it. idk how to change the max calls val or reset it
def test_middleware():
    for _ in range(0, 100):
        client.get('/games/top_games')
    
    response = client.get('games/top_games')
    
    assert response.status_code == 429