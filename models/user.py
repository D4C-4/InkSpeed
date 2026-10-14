"""User domain model."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class User:
    user_id: int
    username: str
    created_at: datetime