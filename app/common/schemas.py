from pydantic import BaseModel


class TokenSchema(BaseModel):
    price: float
    denom: str
    symbol: str
    liquidity: float
    volume_24h: float
    volume_24h_change: float
    name: str
    price_24h_change: float
    price_7d_change: float
    exponent: int
    display: str

    class Config:
        orm_mode = True
