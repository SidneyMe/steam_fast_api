import re
import time

from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

from .game_page_scraper import get_game_info
from mongo_db_processor import MongoRepository, DBEnums
from schemas import GameMetadata, Game


class WebDriver: #requests can't load js so i had to use selenium

    def __init__(self):
        self._webdriver = None

    def __enter__(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-logging')
        self._webdriver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        return self._webdriver

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._webdriver.quit()
        self._webdriver = None


class Parser:

    _STEAM_TOP_URL = 'https://store.steampowered.com/charts/topselling/global'

    def _get_page_source(self):
        page_source = None
        with WebDriver() as driver:
            driver.get(self._STEAM_TOP_URL)
            time.sleep(5) #idk native wait doesn't wait and wait.until doesn't either
            page_source = driver.page_source
        return page_source

    def format_app_ids(self, num_games: int) -> list[Game]:
        html = self._get_page_source()
        apps = re.findall(r'app/\d+/\w+', html)

        game_ids = []
        for app in apps:
            _, appid, app_name = app.replace('_', ' ').split('/') # returns ['app', '730', 'CounterStrike 2']

            if appid == '1675200': #steam deck id
                continue

            game_ids.append(Game(
                appid=appid,
                title=app_name
            ))

            if len(game_ids) >= num_games:
                break

        return game_ids


repository = MongoRepository()

def top_games(num_games: int) -> list[Game]:
    if repository.should_update(DBEnums.LAST_TOP_GAMES_UPDATE):
        repository.clear_top()
        apps = Parser().format_app_ids(99) # just get all games, then strip whatever they want

        for app in apps:
            repository.add_to_top(app.model_dump())

        repository.update_operation_time(DBEnums.LAST_TOP_GAMES_UPDATE)
        return apps[0:num_games]

    else:
        return [Game(**app) for app in repository.get_top(num_games)]

def top_games_metadata(num_games: int) -> list[GameMetadata]:
    games = top_games(num_games)
    games_metadata = []

    for game in games:
        db_game = repository.find_game({'appid': game.appid})
        game_to_add = None

        if db_game:
            game_to_add = GameMetadata(**db_game)
        else:
            game_to_add = get_game_info(game.appid)
            repository.add_game(game_to_add.model_dump())

        games_metadata.append(game_to_add)

    return games_metadata
