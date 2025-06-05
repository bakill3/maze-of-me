"""Emotion-based room templates with random variants."""
import random

ROOMS = {
    "happy": {
        "templates": [
            "Sunbeams dance across {wall_color} walls and a {furniture}. Hope swells as memories of {hook} resurface.",
            "A faint, upbeat melody echoes from the {furniture}—perhaps you remember {hook}?",
            "The scent of citrus lingers, and somewhere a calendar reminder for {hook} whispers from the corners.",
        ],
        "furniture": ["plush sofa", "vintage jukebox", "beanbag"],
        "colors": ["honey yellow", "peach", "warm cream"],
    },
    "sad": {
        "templates": [
            "Muted {wall_color} walls press inwards. A lone {furniture} creaks. Drips echo the countdown to {hook}.",
            "Your footsteps echo like memories you'd rather forget—was it {hook}?",
            "Rain taps the {furniture}. The air is thick with something left unsaid: {hook}.",
        ],
        "furniture": ["rocking chair", "dusty piano", "torn loveseat"],
        "colors": ["washed-out blue", "ashen grey", "cold teal"],
    },
    "angry": {
        "templates": [
            "Ragged shadows slash the {wall_color} walls; a {furniture} rattles. Your pulse matches the room’s fury at {hook}.",
            "Something overturned the {furniture}. Was it anger about {hook}?",
            "The air burns, the {furniture} looks battered—did you remember {hook}?",
        ],
        "furniture": ["metal desk", "barred window", "shattered mirror"],
        "colors": ["scarlet", "burnt umber", "dark crimson"],
    },
    "neutral": {
        "templates": [
            "Bare {wall_color} walls and a simple {furniture}. Silence reigns—only {hook} remains.",
            "A corridor of smooth {wall_color} stretches ahead. {hook} lingers in the quiet air.",
            "The {furniture} waits, perfectly centered. The maze itself seems to pause for {hook}.",
        ],
        "furniture": ["wooden stool", "plain cot", "unmarked door"],
        "colors": ["bone white", "pale beige", "soft grey"],
    },
}

EMOTIONS = list(ROOMS.keys())


def random_room_elements(mood: str, room_number: int) -> tuple[str, str, str]:
    """Return (template, furniture, color) for the given mood."""
    data = ROOMS.get(mood, ROOMS["neutral"])
    tpl = random.choice(data["templates"])
    if room_number and room_number % 5 == 0:
        tpl += " A strange déjà vu clings to the air."
    furn = random.choice(data["furniture"])
    color = random.choice(data["colors"])
    return tpl, furn, color
