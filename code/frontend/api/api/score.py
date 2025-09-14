from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models import Score, Game

router = APIRouter(prefix="/score", tags=["Score"])

class scoreDto(BaseModel):
    id: int
    player: int
    game: int
    score: int

class scoreCreationObject(BaseModel):
    player: int
    game: int
    score: int

@router.post("/", response_model=scoreDto)
async def score(score: scoreCreationObject):
    game = await Game.get(id=score.game)
    returnScore = 0

    if game.player1_id == score.player:
        game.player1Score = max(0, game.player1Score - score.score)
        returnScore = game.player1Score
    elif game.player2_id == score.player:
        game.player2Score = max(0, game.player2Score - score.score)
        returnScore = game.player2Score
    else:
        raise HTTPException(status_code=400, detail="Player not in this game")

    await game.save()

    score_obj = await Score.create(
        player_id=score.player,
        game_id=score.game,
        score=score.score
    )

    return scoreDto(
        id=score_obj.id,
        player=score.player,
        game=score.game,
        score=returnScore
    )