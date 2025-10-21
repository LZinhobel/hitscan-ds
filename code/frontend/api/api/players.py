from fastapi import APIRouter
from models import Player
from pydantic import BaseModel
router = APIRouter(prefix="/player", tags=["Players"])

class playerDto(BaseModel):
    id: int
    name: str

class playerCreate(BaseModel):
    name: str

@router.get("/", response_model=list[playerDto])
async def list_players():
    return await Player.all()

@router.get("/{id}", response_model=playerDto)
async def get_player(id: int):
    return await Player.get(id=id)


@router.post("/", response_model=playerDto)
async def create_player(player: playerCreate):
    return await Player.create(name= player.name)



