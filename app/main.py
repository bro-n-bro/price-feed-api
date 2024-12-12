from typing import List

import uvicorn
from fastapi import FastAPI, Depends
from fastapi_utils.tasks import repeat_every
from sqlalchemy.orm import Session

from app.common.base import Base
from app.common.crud import get_tokens, sync_tokens
from app.common.schemas import TokenSchema
from app.common.session import engine, get_db, sessionmaker_for_periodic_task


def create_tables():
    Base.metadata.create_all(bind=engine)


def start_application():
    app = FastAPI()
    create_tables()
    return app

FILE_PATH = "last_commit.txt"

def initialize_file():
    try:
        with open(FILE_PATH, "r") as f:
            return f.read()
    except FileNotFoundError:
        with open(FILE_PATH, "w") as f:
            f.write('')
        return ''

data = initialize_file()
app = start_application()


@app.get("/tokens/", response_model=List[TokenSchema])
def read_users(symbol__in: str = '', db: Session = Depends(get_db)):
    return get_tokens(symbol__in, db)


@app.on_event("startup")
@repeat_every(seconds=1800)
def sync_tokens_task() -> None:
    with sessionmaker_for_periodic_task.context_session() as db:
        sync_tokens(db)


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)
