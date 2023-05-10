from typing import List
from pydantic import parse_obj_as
from sqlalchemy import func

import requests
from sqlalchemy.orm import Session

from app.common.models import Token
from app.common.schemas import TokenSchema


def get_tokens(symbol__in: str, db: Session):
    if symbol__in:
        return db.query(Token).filter(func.lower(Token.symbol).in_(symbol__in.lower().split(','))).all()
    else:
        return db.query(Token).all()


def sync_tokens(db: Session):
    response = requests.get('https://api-osmosis.imperator.co/tokens/v2/all')
    if response.ok:
        tokens = parse_obj_as(List[TokenSchema], response.json())
        token_to_create = []
        for token in tokens:
            db_token_query = db.query(Token).filter(Token.denom == token.denom)
            if db_token_query.first():
                db_token_query.update(token.dict())
            else:
                token_to_create.append(token)
        for token in token_to_create:
            db_token = Token(**token.dict())
            db.add(db_token)
        db.commit()
