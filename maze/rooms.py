# File: maze/rooms.py
"""
Pre-made emotion rooms.
Each entry returns (description_template, furniture_choices)
The template can reference {name} and {event}.
"""

ROOMS = {
    "happy": (
        "Sun-flecked rays paint the {wall_color} walls while a faint scent of citrus hangs in the air. "
        "A plush {furniture} invites you to linger, and somewhere a music box plays a tune you almost remember.",
        ["yellow sofa", "swinging hammock", "velvet armchair"],
        ["peach-pink", "buttercream", "pastel-green"],
    ),
    "sad": (
        "Muted light drips through cracks in the {wall_color} plaster. Rainwater beads on a forgotten {furniture}. "
        "Your footsteps echo like memories you’d rather forget.",
        ["rocking chair", "dusty piano bench", "folding cot"],
        ["slate-grey", "indigo", "ashen"],
    ),
    "angry": (
        "The {wall_color} bricks feel hot to the touch. A toppled {furniture} blocks part of the room, "
        "scratch-marks scoring the floorboards like claw-marks.",
        ["iron table", "barricaded chest", "splintered desk"],
        ["crimson", "rust-brown", "scorched-black"],
    ),
    "neutral": (
        "A corridor of smooth {wall_color} concrete stretches ahead. A plain {furniture} sits perfectly centred, "
        "as though waiting for purpose.",
        ["wooden stool", "steel locker", "low bench"],
        ["bone-white", "pale-grey", "ecru"],
    ),
}
