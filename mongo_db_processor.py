from datetime import datetime
from enum import StrEnum

from pymongo import MongoClient, IndexModel
from pymongo.database import Collection

from schemas import GameMetadata

class DBEnums(StrEnum):
    LAST_TOP_GAMES_UPDATE = 'last_top_games_update'

class CollectionNames(StrEnum):
    STEAM_GAME_IDS = 'steam_game_ids'
    STEAM_APPS = 'steam_apps'
    APP_METADATA = 'app_metadata'
    TOP_GAMES = 'top_games'
    APPLIST = 'applist'


class MongoConnector:

    def __init__(self, connection_string: str = 'mongodb://localhost:27017/'):
        self.client: MongoClient = MongoClient(connection_string)

    def get_database(self, db_name: str = 'steam'):
        return self.client[db_name]

    def get_collection(self,  collection_name: str, db_name: str = 'steam'):
        return self.client[db_name][collection_name]

class MongoCollections:

    def __init__(self):
        connector = MongoConnector()
        self._game_id_collection: Collection = connector.get_collection(CollectionNames.STEAM_GAME_IDS)
        self._steam_apps_collection: Collection = connector.get_collection(CollectionNames.STEAM_APPS)
        self._app_metadata: Collection = connector.get_collection(CollectionNames.APP_METADATA)
        self._top_games: Collection = connector.get_collection(CollectionNames.TOP_GAMES)
        self._applist: Collection = connector.get_collection(CollectionNames.APPLIST)
        self.__create_indexes()

    def __create_indexes(self):
        #indexes are useless on objects
        indexes = [index for index in GameMetadata.model_fields.keys() if index not in ('editions','developers')]

        for index in indexes:
            if index == 'appid':
                self._steam_apps_collection.create_index(index, unique=True)
            else:
                self._steam_apps_collection.create_index(index, collation={'locale': 'en_US', 'strength': 2})

        developer_index = IndexModel('developers.developer')
        publisher_index = IndexModel('developers.publisher')

        self._steam_apps_collection.create_indexes([developer_index, publisher_index])

    @property
    def game_id_collection(self):
        return self._game_id_collection

    @property
    def steam_apps_collection(self):
        return self._steam_apps_collection

    @property
    def app_metadata(self):
        return self._app_metadata

    @property
    def top_games(self):
        return self._top_games

    @property
    def applist(self):
        return self._applist


class MongoRepository:

    def __init__(self):
        self._collections = MongoCollections()

    def find_games(self, queries: list, price_search: dict[str, int] | None = None):
        if price_search:
            if not queries:
                queries.append({})

            return self._collections.steam_apps_collection.aggregate([
                {'$addFields': {
                    'editionsArray': {
                        '$objectToArray': '$editions'
                    }
                }},
                {'$match': {
                    'editionsArray.v': price_search,
                    '$or': queries
                }}
            ],
            collation={'locale': 'en_US', 'strength': 2})
        else:
            return self._collections.steam_apps_collection.aggregate([
                {'$match':
                    {'$or': queries}
                }],
                collation={'locale': 'en_US', 'strength': 2})

    def search_games(self, text: str):
        return self._collections.steam_apps_collection.find({'$text': {'$search': text}})

    def find_game(self, query):
        return self._collections.steam_apps_collection.find_one(query, {'_id': 0})

    def find_first_game(self):
        return self._collections.steam_apps_collection.find_one({}, {'_id': 0})

    def add_game(self, game):
        if not self.find_game({'appid': game.get('appid')}):
            self._collections.steam_apps_collection.insert_one(game)

    def get_len(self):
        return self._collections.steam_apps_collection.count_documents({})

    def add_to_top(self, game):
        self._collections.top_games.insert_one(game)

    def clear_top(self):
        self._collections.top_games.delete_many({})

    def delete_game(self, appid: int):
        self._collections.steam_apps_collection.delete_one({'appid': appid})

    def get_top(self, num_games: int):
        return self._collections.top_games.find({}, {'_id': 0}).limit(num_games)

    def insert_applist(self, applist: dict):
        self._collections.applist.delete_many({}) # easier to drop everything than check all 250k games
        self._collections.applist.insert_many(applist)

    def update_operation_time(self, operation: str):
        self._collections.app_metadata.update_one(
        {'operation': operation},
        {'$set': {'last_update': datetime.now()}},
        upsert=True
        )

    def should_update(self, operation: str, hours: int = 1) -> bool:

        def _get_last_operation(operation: str) -> datetime | None:
            last_operation = self._collections.app_metadata.find_one({
                'operation': operation
            })
            return last_operation['last_update'] if last_operation else None


        last_update = _get_last_operation(operation)
        if not last_update:
            return True

        time_diff = datetime.now() - last_update
        return time_diff.total_seconds() >= (hours * 3600)
