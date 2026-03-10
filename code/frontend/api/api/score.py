from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.openapi.models import Response
from pydantic import BaseModel

from api.players import playerDto
from models import Score, Game

router = APIRouter(prefix="/score", tags=["Score"])

class scoreDto(BaseModel):
    id: int
    player_id: int
    game_id: int
    score: int

class scoreCreationObject(BaseModel):
    player: int
    game: int
    score: int

@router.post("/", response_model=scoreDto)
async def score(score: scoreCreationObject):
    game = await Game.get(id=score.game)

    if game.player1_id == score.player:
        game.player1Score -= score.score
        returnScore = game.player1Score
    elif game.player2_id == score.player:
        game.player2Score -= score.score
        returnScore = game.player2Score
    else:
        raise HTTPException(status_code=400, detail="Player not in this game")

    await game.save()

    score_obj = await Score.create(
        player_id=score.player,
        game_id=score.game,
        score=score.score
    )

    return scoreDto(id=score_obj.id, player_id=score.player, game_id=score.game, score=returnScore)

@router.get("/{player_id}", response_model=List[scoreDto])
async def get_scores(player_id: int):
    return await Score.filter(player_id=player_id).values(
        "id",
        "score",
        "player_id",
        "game_id"
    )

@router.delete("/reset/{player_id}")
async def reset_scores(player_id: int):
    deleted_count = await Score.filter(player_id=player_id).delete()
    return  {"deleted": deleted_count}

@router.delete("/{score_id}")
async def delete_score(score_id: int):
    score_obj = await Score.get_or_none(id=score_id)
    if not score_obj:
        raise HTTPException(status_code=404, detail="Score not found")

    game = await Game.get(id=score_obj.game_id)

    if game.player1_id == score_obj.player_id:
        game.player1Score += score_obj.score
    elif game.player2_id == score_obj.player_id:
        game.player2Score += score_obj.score
    else:
        raise HTTPException(status_code=400, detail="Player not in this game")

    await game.save()
    await score_obj.delete()

    return {"player1Score": game.player1Score, "player2Score": game.player2Score}