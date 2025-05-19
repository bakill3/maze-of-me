# utils/parsers.py
import re
from datetime import datetime, date
from typing import Union
from config import Config

def parse_height(raw: str) -> float:
    """
    Accepts inputs like "178", "1.78", "1,78m", "178cm" and returns height in cm.
    Rules:
      - If unit "cm" → treat as cm.
      - If unit "m"  → treat as meters.
      - If no unit and value ≤ 2.0 → treat as meters.
      - If no unit and value  > 2.0 → treat as centimeters.
    """
    s = raw.strip().lower().replace(',', '.')
    unit = None

    if s.endswith('cm'):
        unit = 'cm'
        s = s[:-2].strip()
    elif s.endswith('m'):
        unit = 'm'
        s = s[:-1].strip()

    # s should now be just a number
    try:
        val = float(s)
    except ValueError:
        raise ValueError(f"Couldn’t parse height value from '{raw}'")

    # Determine cm
    if unit == 'cm':
        cm = val
    elif unit == 'm':
        cm = val * 100
    else:
        # No unit given
        if val <= 2.0:
            cm = val * 100
        else:
            cm = val

    if not (Config.MIN_HEIGHT_CM <= cm <= Config.MAX_HEIGHT_CM):
        raise ValueError(f"Height {cm:.2f} cm out of range [{Config.MIN_HEIGHT_CM}, {Config.MAX_HEIGHT_CM}]")

    return round(cm, 2)

def parse_weight(raw: str) -> float:
    """
    Accepts inputs like "70", "70kg", "70,5" and returns weight in kg.
    """
    s = raw.strip().lower().replace(',', '.')
    if s.endswith('kg'):
        s = s[:-2].strip()
    try:
        val = float(s)
    except ValueError:
        raise ValueError(f"Couldn’t parse weight value from '{raw}'")
    if not (Config.MIN_WEIGHT_KG <= val <= Config.MAX_WEIGHT_KG):
        raise ValueError(f"Weight {val:.2f} kg out of range [{Config.MIN_WEIGHT_KG}, {Config.MAX_WEIGHT_KG}]")
    return round(val, 2)

def parse_eu_date(raw: str) -> date:
    """
    Parses DD-MM-YYYY (or D-M-YYYY) and returns a date object.
    """
    try:
        return datetime.strptime(raw.strip(), '%d-%m-%Y').date()
    except ValueError as e:
        raise ValueError("Date must be in DD-MM-YYYY format") from e
