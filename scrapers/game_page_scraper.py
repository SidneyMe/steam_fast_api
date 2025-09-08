import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from bs4.element import PageElement

from schemas import GameMetadata

class PageScraper:

    STEAM_URL = 'https://store.steampowered.com/app/{appid}'

    def __init__(self, appid: int):
        self.appid = appid
        self.soup = None
        self._fetch_page()

    def _fetch_page(self):

        def _is_parsed():
            return self.soup is not None

        try:
            resp = requests.get(self.STEAM_URL.format(appid=self.appid), timeout=10).text
            self.soup = BeautifulSoup(resp, 'html.parser')
            if not _is_parsed():
                raise requests.exceptions.Timeout()
        except (requests.ConnectionError, requests.ConnectTimeout) as bad_connection:
            raise Exception from bad_connection

    def get_title(self) -> str:
        return self.soup.find('div', class_='apphub_AppName').text

    def get_description(self) -> str:
        try:
            return self.soup.find('div', class_='game_description_snippet').text.strip()
        except AttributeError:
            return self.soup.find('div', class_='glance_details').text.strip()

    def get_release_date(self) -> datetime:
        return datetime.strptime(self.soup.find('div', class_='date').text, '%d %b, %Y')

    def get_developers(self) -> dict[str, str]:
        dev_publisher_info = {}

        for dev_row in self.soup.find('div', class_='glance_ctn_responsive_left').find_all('div', class_='dev_row'):
            dev_type = dev_row.find('div', class_='subtitle column').text.lower().removesuffix(':')
            dev_name = dev_row.find('div', class_='summary column').a.text
            dev_publisher_info[dev_type] = dev_name

        return dev_publisher_info

    def get_tags(self) -> list[str]:
        game_tags = []
        for app_tag in self.soup.find('div', class_='rightcol').find_all('a', class_='app_tag'):
            tag = app_tag.text
            game_tags.append(tag.strip())
        
        return game_tags

    def get_editions(self) -> dict[str, float]:
    
        game_editions = {}

        def _clean_edition_name(name: str) -> str:
            for prefix in ['Buy', 'Pre-Purchase', 'Play']:
                if name.startswith(prefix):
                    name = name.removeprefix(prefix)
            if 'BUNDLE' in name:
                name = name.split('BUNDLE')[0].strip()
            return name

        def _search_edition_price(purchase_area: PageElement) -> None:

            try:
                edition = purchase_area.find('h2', class_='title').text.strip()
                edition = _clean_edition_name(edition)

                price = None

                if 'Free To Play' in purchase_area.find('div', class_='game_purchase_action').text:
                    price = 0.0
                else:
                    class_electors = ['game_purchase_price', 'discount_block game_purchase_discount', 'discount_block game_purchase_discount no_discount']

                    for selector in class_electors:
                        price_area = purchase_area.find('div', class_=selector)
                        if price_area:
                            try:
                                price = price_area['data-price-final']
                                break
                            except KeyError:
                                price = price_area.find_next('div', class_='your_price_label').text.strip()
                                price = re.search(r'\d+', price).group(0)

                    price = float(int(price) / 100) # default format is 10000 for $100

                game_editions[edition] = price

            except (AttributeError, ValueError, TypeError):
                pass


        selectors = ['game_area_purchase_game_wrapper', 'game_area_purchase']

        for selector in selectors:
            try:
                for purchase_area in self.soup.find_all('div', class_=selector):
                    _search_edition_price(purchase_area)

            except AttributeError:
                pass

        return game_editions

    def get_game_features(self) -> list[str] | None:
        game_features = []
        try:
            for feature_tag in self.soup.find('div', class_='game_area_features_list_ctn').find_all('div', class_='label'):
                feature = feature_tag.text
                game_features.append(feature)
        except AttributeError:
            game_features = None
        return game_features


def validate_game(gameid) -> bool:
    resp = requests.get(f'https://store.steampowered.com/app/{gameid}', timeout=10).url
    return f'/app/{gameid}' in resp


def get_game_info(appid):
    if validate_game(appid):
        parser = PageScraper(appid=appid)
        game = GameMetadata(
            appid=appid,
            title=parser.get_title(),
            description=parser.get_description(),
            release_date=parser.get_release_date(),
            developers=parser.get_developers(),
            tags=parser.get_tags(),
            editions=parser.get_editions(),
            features=parser.get_game_features()
        )
        return game
    else:
        return None
