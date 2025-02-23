import json
import os
from typing import List

import git
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


REPO_OWNER = "bro-n-bro"
REPO_NAME = "chain-registry"
BRANCH_NAME = "main"
REPO_URL = "https://github.com/bro-n-bro/chain-registry.git"
REPO_PATH = "./chain-registry"


def get_latest_commit_hash():
    url = f"https://api.github.com/repos/bro-n-bro/chain-registry/commits/master"
    response = requests.get(url)
    if response.status_code == 200:
        commit_data = response.json()
        return commit_data['sha']
    else:
        return None

def get_stored_commit_hash():
    try:
        with open('last_commit.txt', "r") as file:
            return file.readline().strip()
    except FileNotFoundError:
        return None

def write_new_commit_hash(new_value):
    with open('last_commit.txt', "w") as file:
        file.write(new_value)

def clone_repo():
    git.Repo.clone_from(REPO_URL, REPO_PATH)

def pull_repo():
    repo = git.Repo(REPO_PATH)
    origin = repo.remotes.origin
    origin.pull("master")

def check_and_update_repo():
    if not os.path.exists(REPO_PATH):
        clone_repo()
    else:
        try:
            pull_repo()
        except git.exc.InvalidGitRepositoryError:
            clone_repo()


def find_assetlist_json():
    assetlist_data = []

    for root, dirs, files in os.walk(REPO_PATH):
        if root == REPO_PATH:
            for dir_name in dirs:
                folder_path = os.path.join(root, dir_name)
                assetlist_path = os.path.join(folder_path, 'assetlist.json')
                if os.path.exists(assetlist_path):
                    try:
                        with open(assetlist_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            for asset in data['assets']:
                                if asset.get('coingecko_id'):
                                    assetlist_data.append({
                                        'denom': next(
                                            (item['denom'] for item in asset['denom_units'] if item['exponent'] == 0),
                                            'Not defined in skychart'),
                                        'exponent': max([item['exponent'] for item in asset['denom_units']]),
                                        'name': asset['name'],
                                        'display': asset['display'],
                                        'coingecko_id': asset['coingecko_id'],
                                        'liquidity': 0,
                                        'volume_24h': 0,
                                        'volume_24h_change': 0,
                                        'price_7d_change': 0
                                    })
                    except (json.JSONDecodeError, OSError) as e:
                        print(f"Read error {assetlist_path}: {e}")
    return assetlist_data

def get_tokens_with_coingecko_info(tokens, coingecko_info):
    final_result = []
    for item in tokens:
        coingecko = next(
            (coingecko_data for coingecko_data in coingecko_info if coingecko_data['id'] == item['coingecko_id']), None)
        if coingecko:
            item['symbol'] = coingecko['symbol']
            item['price'] = coingecko['current_price']
            item['price_24h_change'] = coingecko['price_change_percentage_24h']
            item.pop('coingecko_id')
            if item['price']:
                final_result.append(item)
    return final_result

def save_tokens_to_db(db, final_result):
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
    try:
        db.commit()
        print("Committed successfully")
    except Exception as e:
        db.rollback()
        print(f"Error during commit: {e}")

def remove_duplicates(final_result):
    seen_coingecko_ids = set()
    seen_denoms = set()
    denom_map = {}

    for item in final_result:
        coingecko_id = item['coingecko_id']
        denom = item['denom']

        if not item['denom'].startswith('IBC/'):
            if coingecko_id not in seen_coingecko_ids and denom not in seen_denoms:
                seen_coingecko_ids.add(coingecko_id)
                seen_denoms.add(denom)
                denom_map[coingecko_id] = item

    filtered_data = list(denom_map.values())  # Start with non-IBC items

    for item in final_result:
        coingecko_id = item['coingecko_id']
        denom = item['denom']

        if item['denom'].startswith('IBC/') and coingecko_id not in denom_map and denom not in seen_denoms:
            filtered_data.append(item)
            seen_denoms.add(denom)
    return filtered_data

def append_default_tokens(tokens):
    tokens.append({'denom': 'btc', 'exponent': 1, 'name': 'Bitcoin', 'display': 'btc', 'coingecko_id': 'bitcoin', 'liquidity': 0, 'volume_24h': 0, 'volume_24h_change': 0, 'price_7d_change': 0})
    tokens.append({'denom': 'eth', 'exponent': 1, 'name': 'Ethereum', 'display': 'eth', 'coingecko_id': 'ethereum', 'liquidity': 0, 'volume_24h': 0, 'volume_24h_change': 0, 'price_7d_change': 0})
    tokens.append({'denom': 'elys', 'exponent': 1, 'name': 'Elys', 'display': 'elys', 'coingecko_id': 'elys-network', 'liquidity': 0, 'volume_24h': 0, 'volume_24h_change': 0, 'price_7d_change': 0})


def sync_tokens(db: Session):
    latest_commit_hash = get_latest_commit_hash()
    if latest_commit_hash:
        stored_commit_hash = get_stored_commit_hash()
        if latest_commit_hash != stored_commit_hash:
            check_and_update_repo()
            write_new_commit_hash(latest_commit_hash)
    tokens = find_assetlist_json()
    tokens = remove_duplicates(tokens)
    append_default_tokens(tokens)
    coingecko_ids = [token['coingecko_id'] for token in tokens]
    coingecko_info = get_info_for_all_coins_from_coingecko(coingecko_ids)
    final_result = get_tokens_with_coingecko_info(tokens, coingecko_info)
    save_tokens_to_db(db, final_result)
