import requests

def scrape_ids():
    response = requests.get('https://api.steampowered.com/ISteamApps/GetAppList/v2', timeout=10).json()
    return response['applist']
