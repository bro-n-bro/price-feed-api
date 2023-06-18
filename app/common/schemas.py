from typing import Optional

from pydantic import BaseModel


class TokenSchema(BaseModel):
    price: float
    denom: str
    symbol: str
    liquidity: Optional[float] = None
    volume_24h: Optional[float] = None
    volume_24h_change: Optional[float] = None
    name: str
    price_24h_change: Optional[float] = None
    price_7d_change: Optional[float] = None
    exponent: int
    display: str

    class Config:
        orm_mode = True
