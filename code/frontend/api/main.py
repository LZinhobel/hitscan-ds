from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise
from api import players,games,score
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.include_router(players.router)
app.include_router(games.router)
app.include_router(score.router)


origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tortoise ORM config
register_tortoise(
    app,
    db_url="sqlite://db.sqlite",
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)
