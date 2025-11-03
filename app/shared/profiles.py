from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class UserProfile:
    user: str
    timezone: str
    full_name: Optional[str] = None


class ProfileDirectory:
    """Simple in-memory user profile store keyed by handle."""

    def __init__(self, csv_path: Optional[Path] = None):
        self._profiles: Dict[str, UserProfile] = {}
        if csv_path and csv_path.exists():
            self.load_csv(csv_path)

    def load_csv(self, csv_path: Path) -> None:
        with csv_path.open("r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                handle = row.get("user") or row.get("handle")
                timezone = row.get("timezone")
                if not handle or not timezone:
                    continue
                profile = UserProfile(
                    user=handle,
                    timezone=timezone,
                    full_name=row.get("full_name"),
                )
                self._profiles[handle.lower()] = profile

    def get(self, user: str) -> Optional[UserProfile]:
        return self._profiles.get(user.lower())
