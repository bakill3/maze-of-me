# llm_worker.py
import sys
import json
from utils.json_io import load_json
from maze.generator import MazeGenerator

if __name__ == "__main__":
    req = sys.stdin.read()
    req_data = json.loads(req)
    # Build profile, room, and log objects exactly as needed
    profile = req_data["profile"]
    room = req_data["room"]
    log = req_data["log"]
    action = req_data.get("action", "greeting")
    # Minimal MazeGenerator to handle prompt construction
    maze = MazeGenerator(profile)
    class DummyRoom:
        def __init__(self, desc, theme, furniture):
            self.description = desc
            self.theme = theme
            self.furniture = furniture
    d_room = DummyRoom(room["description"], room["theme"], room["furniture"])
    npc_reply, _ = maze.talk_with_context(action, d_room, log)
    print(npc_reply)
