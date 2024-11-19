from typing import List
from pydantic import parse_obj_as
from sqlalchemy import func

import requests
from sqlalchemy.orm import Session

from app.common.models import Token
from app.common.schemas import TokenSchema
from config import COINGECKO_API_KEY


def get_tokens(symbol__in: str, db: Session):
    if symbol__in:
        return db.query(Token).filter(func.lower(Token.symbol).in_(symbol__in.lower().split(','))).all()
    else:
        return db.query(Token).all()

def make_get_requests_to_coingecko(request_urls):
    result = []
    for url in request_urls:
        response = requests.get(url)
        result += response.json()
    return result

def get_info_for_all_coins_from_coingecko(coins_ids):

    request_urls = []
    current_url = f'https://api.coingecko.com/api/v3/coins/markets?x_cg_demo_api_key={COINGECKO_API_KEY}&vs_currency=usd&per_page=250&'
    for coingecko_id in coins_ids:
        if len(coingecko_id) + len(current_url) > 2048:
            request_urls.append(current_url)
            current_url = f'https://api.coingecko.com/api/v3/coins/markets?x_cg_demo_api_key={COINGECKO_API_KEY}&vs_currency=usd&per_page=250&ids={coingecko_id}'
        else:
            if 'ids' in current_url:
                current_url += f',{coingecko_id}'
            else:
                current_url += f'ids={coingecko_id}'
    request_urls.append(current_url)
    return make_get_requests_to_coingecko(request_urls)


def sync_tokens(db: Session):
    response = requests.get('https://skychart.bronbro.io/v1/assets')
    result = []
    coingecko_ids = []
    for symbol in set(response.json()):
        response = requests.get(f'https://skychart.bronbro.io/v1/asset/{symbol}')
        if response.status_code == 200 and 'coingecko_id' in response.json():
            coin = response.json()
            result.append({
                'denom': next((item['denom'] for item in coin['denom_units'] if item['exponent'] == 0),
                              'Not defined in skychart'),
                'exponent': max([item['exponent'] for item in coin['denom_units']]),
                'name': coin['name'],
                'display': coin['display'],
                'coingecko_id': coin['coingecko_id'],
                'liquidity': 0,
                'volume_24h': 0,
                'volume_24h_change': 0,
                'price_7d_change': 0
            })
            coingecko_ids.append(coin['coingecko_id'])

    coingecko_info = get_info_for_all_coins_from_coingecko(coingecko_ids)
    final_result = []
    for item in result:
        coingecko = next(
            (coingecko_data for coingecko_data in coingecko_info if coingecko_data['id'] == item['coingecko_id']), None)
        if coingecko:
            item['symbol'] = coingecko['symbol']
            item['price'] = coingecko['current_price']
            item['price_24h_change'] = coingecko['price_change_percentage_24h']
            item.pop('coingecko_id')
            if item['price']:
                final_result.append(item)
    tokens = parse_obj_as(List[TokenSchema], final_result)
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
