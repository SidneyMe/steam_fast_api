from datetime import datetime
from pydantic import BaseModel

class Game(BaseModel):
    appid: int
    title: str | None


class GameMetadata(Game):

    description: str | None
    release_date: datetime | None
    developers: dict[str, str] | None
    tags: list[str] | None
    editions: dict[str, float] | None
    features: list[str] | None
