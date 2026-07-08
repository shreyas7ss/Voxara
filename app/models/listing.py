from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class Listing(SQLModel, table=True):
    __tablename__ = "listings"

    id: Optional[int] = Field(default=None, primary_key=True)
    agent_number: str
    raw_caption: str = ""

    property_type: Optional[str] = None
    location: Optional[str] = None
    price_text: Optional[str] = None
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    bedrooms: Optional[str] = None
    furnishing: Optional[str] = None
    amenities: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))

    image_urls: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    listing_summary: Optional[str] = None
    availability_status: str = "available"

    message_sid: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
