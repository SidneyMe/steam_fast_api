# Steam API Project

A FastAPI-based web scraper and API for Steam game data with MongoDB storage and rate limiting.

## Features

- **Game Search & Discovery**: Search games by various criteria (title, developer, tags, price range, etc.)
- **Top Games Tracking**: Fetch and cache Steam's top-selling games
- **Game Metadata Scraping**: Extract detailed game information from Steam store pages
- **MongoDB Integration**: Persistent storage with indexed collections
- **Rate Limiting**: Built-in request limiting middleware

## Installation

1. Clone the repository:
```bash
git clone https://github.com/SidneyMe/steam_fast_api.git
cd steam_api
```

2. Install dependencies:
```bash
pip install -r req.txt
```

3. Start MongoDB:
```bash
# Using Docker
docker run -d -p 27017:27017 --name mongodb mongo

# Or install MongoDB locally
```

4. Run the application:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Games

- `GET /games` - Get all games in the database
- `POST /games/{appid}` - Add a specific game by Steam App ID
- `GET /games/search` - Search games with various filters
- `GET /games/top_games` - Get top-selling games (basic info)
- `GET /games/top_games_info` - Get top-selling games with full metadata
- `GET /games/applist` - Get all existing games and their titles in Steam

### Search Parameters

The `/games/search` endpoint supports the following query parameters:

- `appid` - Steam Application ID
- `title` - Game title (partial match)
- `description` - Game description (partial match)
- `release_date` - Release date
- `developers` - List of developers
- `publishers` - List of publishers
- `tags` - List of game tags
- `features` - List of game features
- `edition_min` - Minimum price
- `edition_max` - Maximum price

### Example Requests

```bash
# Search by title
GET /games/search?title=Counter-Strike

# Search by price range
GET /games/search?edition_min=10&edition_max=50

# Search by developer
GET /games/search?developers=Valve

# Get top 10 games
GET /games/top_games?num_games=10
```

## Project Structure

```
steam_api/
├── main.py
├── schemas.py
├── mongo_db_processor.py
├── middleware.py
├── scrapers/
│   ├── game_page_scraper.py    # Steam store page scraper
│   ├── game_id_scraper.py      # Steam app list scraper
│   └── populate_db.py          # Top games scraper
└── readme.md
```


## Rate Limiting

- Default: 100 requests per 10-second window per IP

## Database Collections

- `steam_apps`: Main game metadata storage
- `top_games`: Cached top-selling games
- `app_metadata`: Operation timestamps and metadata
- `applist`: Complete Steam application list
- `steam_game_ids`: Game ID tracking

## Tech Stack

- **Backend**: FastAPI, Python 3.11+
- **Database**: MongoDB
- **Web Scraping**: BeautifulSoup4, Selenium
- **Data Validation**: Pydantic
- **HTTP Client**: Requests

## License

This project is for educational purposes. Please respect Steam's Terms of Service.