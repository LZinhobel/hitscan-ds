from datetime import datetime

from fastapi import APIRouter
from models import Game, Player
from pydantic import BaseModel, ConfigDict
from .players import playerDto
router = APIRouter(prefix="/game", tags=["Games"])


class PlayerDto(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class GameCreate(BaseModel):
    player1: int
    player2: int
    version: str  # "301" | "501"


class GameDto(BaseModel):
    gameId: int
    date: datetime
    player1: PlayerDto
    player1Score: int
    player2: PlayerDto
    player2Score: int

@router.get("/", response_model=list[GameDto])
async def get_games():
        return await Game.all()

@router.get("/{gameId}", response_model=GameDto)
async def get_game(gameId: int):
    return await Game.get(id = gameId)

@router.post("/", response_model=GameDto)
async def create_game(payload: GameCreate):
    base = 301 \
        if payload.version == "301" else 501

    new_game = await Game.create(
        date=datetime.now(),
        player1_id=payload.player1,
        player2_id=payload.player2,
        player1Score=base,
        player2Score=base,
    )

    await new_game.fetch_related("player1", "player2")

    return GameDto(
        gameId=new_game.id,
        date=new_game.date,
        player1=PlayerDto.model_validate(new_game.player1),
        player1Score=new_game.player1Score,
        player2=PlayerDto.model_validate(new_game.player2),
        player2Score=new_game.player2Score,
    )

@router.patch("/setWinner", response_model=bool)
async def update_winner(gameId: int, winnerId: int):
    await Game.filter(id=gameId).update(winnerId = winnerId)
    return True

