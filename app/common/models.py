from sqlalchemy import Column, Integer, String, Float

from app.common.base_class import Base


class Token(Base):
    id = Column(Integer, primary_key=True, index=True)
    price = Column(Float())
    denom = Column(String, nullable=False, unique=True)
    symbol = Column(String, nullable=False, unique=True)
    liquidity = Column(Float())
    volume_24h = Column(Float())
    volume_24h_change = Column(Float())
    name = Column(String, nullable=False)
    price_24h_change = Column(Float())
    price_7d_change = Column(Float())
    exponent = Column(Integer)
    display = Column(String, nullable=False)
