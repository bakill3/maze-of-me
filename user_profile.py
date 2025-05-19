import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
from config import Config
from utils.json_io import load_json, save_json
from utils.parsers import parse_height, parse_weight, parse_eu_date

logger = logging.getLogger(__name__)

@dataclass
class UserProfile:
    full_name: str
    birthdate: str        # ISO YYYY-MM-DD
    age: int
    height_cm: float
    weight_kg: float
    eye_color: str
    hair_color: str
    skin_color: str
    created_at: str       # UTC ISO

    @classmethod
    def collect(cls) -> 'UserProfile':
        logger.info("Starting profile collection")
        while True:
            # Full name
            while True:
                name = input("Full name: ").strip()
                if name:
                    break
                print("  ❌ Name can’t be empty.")

            # Birthdate
            while True:
                dob_raw = input("Date of birth (DD-MM-YYYY): ").strip()
                try:
                    dob = parse_eu_date(dob_raw)
                    if dob >= datetime.now().date():
                        print("  ❌ Birthdate must be in the past.")
                        continue
                    break
                except ValueError as e:
                    print(f"  ❌ {e}")

            # Age
            while True:
                age_raw = input("Age: ").strip()
                if not age_raw.isdigit():
                    print("  ❌ Age must be a whole number.")
                    continue
                age = int(age_raw)
                if not (Config.MIN_AGE <= age <= Config.MAX_AGE):
                    print(f"  ❌ Age must be between {Config.MIN_AGE} and {Config.MAX_AGE}.")
                    continue
                break

            # Height
            while True:
                h_raw = input("Height (e.g. 178, 1.78, 1,78m): ")
                try:
                    height_cm = parse_height(h_raw)
                    break
                except ValueError as e:
                    print(f"  ❌ {e}")

            # Weight
            while True:
                w_raw = input("Weight (e.g. 70, 70kg): ")
                try:
                    weight_kg = parse_weight(w_raw)
                    break
                except ValueError as e:
                    print(f"  ❌ {e}")

            # Appearance
            def ask(field: str) -> str:
                while True:
                    v = input(f"{field}: ").strip()
                    if v:
                        return v
                    print(f"  ❌ {field} can’t be empty.")

            eye_color  = ask("Eye color")
            hair_color = ask("Hair color")
            skin_color = ask("Skin color")

            created_at = datetime.utcnow().isoformat() + 'Z'

            profile = cls(
                full_name=name,
                birthdate=dob.isoformat(),
                age=age,
                height_cm=height_cm,
                weight_kg=weight_kg,
                eye_color=eye_color,
                hair_color=hair_color,
                skin_color=skin_color,
                created_at=created_at
            )

            # Confirmation
            print("\nPlease confirm your profile:")
            for k, v in asdict(profile).items():
                if k == 'created_at':
                    continue
                print(f"  {k.replace('_',' ').title()}: {v}")
            yn = input("\nIs this correct? (Y/n): ").strip().lower()
            if yn in ('', 'y', 'yes'):
                logger.info("Profile confirmed by user")
                return profile

            print("\nLet’s try again.\n")
            logger.info("Profile collection restart requested")

    def save(self) -> None:
        save_json(Config.PROFILE_PATH, asdict(self))
        logger.info(f"Profile saved to {Config.PROFILE_PATH}")

    @staticmethod
    def load() -> Optional['UserProfile']:
        data = load_json(Config.PROFILE_PATH)
        if not data:
            logger.debug("No existing profile found")
            return None
        try:
            profile = UserProfile(**data)
            logger.debug("Loaded existing profile")
            return profile
        except TypeError:
            logger.error("Existing profile JSON is invalid")
            return None
