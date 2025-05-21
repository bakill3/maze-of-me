# 🎭 Maze of Me

> *A deeply personal, narrative-driven psychological game built entirely in Python, harnessing user data, emotion, and advanced AI-driven NPC interactions.*

---

## 📖 Overview

**Maze of Me** is a command-line psychological adventure where your digital self is the foundation for a unique, emotional narrative. The game adapts to your profile, calendar, moods, and social connections, creating a different journey every session. Navigate a procedurally generated text maze, meet AI figures who remember your feelings and contacts, and discover how your online presence shapes your subconscious world.

OAuth logins (Spotify, Google, with Facebook & Instagram coming soon) bring in real data to create an interactive and personal experience.

---

## 🧩 Game Concept and Structure

Players awake in a mysterious maze. The story and rooms reference your real-world data, events, moods, and contacts, integrating your digital and emotional life into an interactive psychological narrative:

- **Act 1: Awakening**  
  Bright rooms and supportive AI figures welcome you. Upbeat music, selected from your top Spotify tracks and YouTube history, enhances the mood.

- **Act 2: Whispers**  
  Rooms and AI figures reference real calendar events, friends, or memories. NPCs become more challenging, sometimes asking about people in your contacts or your recent mood.

- **Act 3: Collapse and Reflection**  
  The maze responds to your feedback, looping through memories and feelings until you reach deeper self-understanding or choose to start over.

---

## 🔑 Features

### ✅ Automated User Data Collection
- **Google OAuth**  
  - Fetches profile info, calendar events, YouTube history, and contacts (names, emails, birthdays).
- **Spotify OAuth**  
  - Collects your top tracks, audio features (valence, energy), and artists for music and narrative context.

### ✅ Emotion-Aware AI Gameplay
- **Procedural Maze Generation**  
  - Every room is generated based on your real events, contacts, moods, and time of day.
  - Room descriptions and layouts are always unique and personalized.
- **Music as Mood**  
  - Each room's emotion is matched to your music using valence and energy from Spotify data.
  - Audio is preloaded using `yt-dlp` for instant playback and played with `pygame`.
  - Previous room's audio files are deleted automatically for optimal performance and minimal disk usage.
- **AI NPCs with Memory and Contact Awareness**  
  - NPCs use your contacts, recent emotions, and previous dialogue to generate deeply personal interactions.
  - The AI always gives a meaningful, context-aware reply, even if some data is missing.
  - Fallback logic ensures the game always continues smoothly.
- **Dialogue Trees**  
  - Each encounter lets you choose how to interact: "Who are you?", "Explain this room", "You’re lying", or "Stay silent".
  - Your emotional reactions (happy, sad, angry, neutral) are remembered and affect future AI responses.
- **AI Loading Spinner**  
  - When the AI is thinking, a real-time spinner keeps the CLI responsive until the NPC responds.
- **NPC Memory**  
  - NPCs can reference your prior feelings, choices, and even earlier NPCs within and across sessions.
- **Inspect and Use Room Items**  
  - You can inspect room furniture for additional context or NPC responses.

### ✅ Enhanced CLI User Experience
- Modern CLI with color, typewriter effect, clear menus, and easy navigation.
- Help menu, graceful exits, and robust error handling.
- Detailed logging of all interactions for transparency and debugging.

---

## 🛠️ Tech Stack

- **Programming Language**: Python 3.13.3
- **CLI Engine**: Custom-built (input, print, color, spinner, typewriter)
- **OAuth Libraries**: `spotipy`, `google-auth`, `requests-oauthlib`
- **Audio Playback**: `pygame`, `yt-dlp`
- **AI Integration**: Local LLM with `llama-cpp-python` (Phi-3, LLaMA, Mistral), Ollama, or LM Studio
- **Data Storage**: JSON files
- **Utilities**: Helpers for parsing, data, and OS/platform detection
- **Cross-Platform**: Runs on Windows, Linux, and macOS

---

## 🧠 System Architecture Diagram

```mermaid
graph TD
  subgraph OAuth["🔐 OAuth Providers"]
    Spotify[Spotify OAuth]
    Google[Google OAuth]
    Facebook[Facebook OAuth (planned)]
    Instagram[Instagram OAuth (planned)]
  end

  subgraph Profile["🧍 User Profile"]
    Contacts[Google Contacts]
    SpotifyData[Spotify Top Tracks + Features]
    GoogleCal[Google Calendar Events]
    YouTube[YouTube Watch History]
    Email[Google Profile Info]
  end

  subgraph CLI["🖥️ Maze CLI"]
    Start[Start Maze]
    Move[Choose Direction]
    Talk[Talk to NPC]
    Inspect[Inspect Room/Furniture]
    Log[Interaction Log & Emotion History]
    UX[CLI Help, Typewriter FX, Spinner, Exit]
  end

  subgraph LLM["🧠 Local AI"]
    PromptGen[Build Prompt (with Contacts, Emotions, Events)]
    RoomGen[Room Description]
    NPCGen[NPC Dialogue + Memory]
  end

  subgraph Audio["🔊 Audio Engine"]
    MoodDetect[Analyze Spotify Valence/Energy]
    TrackPlay[Play YouTube Audio via yt-dlp]
    Cache[Preload & Cleanup Tracks]
  end

  subgraph Future["🚧 Planned Features"]
    FBData[Facebook Data]
    IGData[Instagram Data]
    NPCFriends[NPCs from Real People]
    WebUI[Web-based GUI (optional)]
  end

  Spotify --> SpotifyData
  Google --> Email
  Google --> GoogleCal
  Google --> YouTube
  Google --> Contacts
  Facebook --> FBData
  Instagram --> IGData

  SpotifyData --> Profile
  GoogleCal --> Profile
  YouTube --> Profile
  Email --> Profile
  Contacts --> Profile
  FBData --> Profile
  IGData --> Profile

  Profile --> PromptGen
  PromptGen --> RoomGen
  PromptGen --> NPCGen

  RoomGen --> Start
  NPCGen --> Talk
  RoomGen --> Inspect

  Start --> Move
  Move --> RoomGen
  Talk --> NPCGen
  Inspect --> NPCGen

  Profile --> MoodDetect
  MoodDetect --> TrackPlay
  TrackPlay --> Cache

  FBData --> Future
  IGData --> Future
  Future --> NPCFriends
  Future --> WebUI
```

## Alpha version (spotify auth + random music playlists on each room)

https://github.com/user-attachments/assets/490cff18-db04-40df-bba9-e7dd57f322e3

---

## Current Version

https://github.com/user-attachments/assets/6feb4a40-a53a-40da-9f59-334e3a66992c

---

## 🚀 Installation & Running Locally

### 1. Clone the repository:

```bash
git clone https://github.com/bakill3/maze-of-me.git
cd maze_of_me

### 2. Install dependencies:
```bash
pip install -r requirements.txt
```
### 3. Configure OAuth Credentials
Create a .env file in the root directory with:
```bash
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_secret
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_secret
```

### 4. Download AI Model
To download the required language model, run download.bat inside the models folder before starting the game.

### 5. Run the game:
```bash
python cli.py
```

## 🗺️ Gameplay & AI Roadmap
- [x] Spotify and Google OAuth & Data Collection
- [x] YouTube Audio Preloading, Caching, and Cleanup
- [x] Emotion-driven Room and Music Generation
- [x] AI NPCs Powered by Local LLM, with Memory and Contacts
- [x] Dialogue Trees & Player Emotion Feedback
- [x] Loading Spinner for AI Responses
- [x] Inspect & Use Room Items
- [x] Per-Room Audio Cleanup for Performance
- [x] NPCs Reference Contacts, Real Events, and Player Emotions
- [ ] Facebook & Instagram Integration (planned)
- [ ] Persistent Cross-Session NPC Memory (planned)
- [ ] Optional Web-based GUI (planned)

---

## 🧪 Testing

Unit tests for all critical parsing and CLI logic.  
To run tests:
```bash
pytest tests/test_parsers.py
```

## ⚠️ Disclaimer & Privacy

**Maze of Me** places the highest priority on user privacy and data security:

- All user data collected via OAuth or manual input is stored **locally** and **never shared externally**.
- OAuth authentication tokens and sensitive data are securely handled and stored only for local use within gameplay.

---

## 🌟 Contribution & Feedback

Maze of Me is open to your ideas!
Open an issue, fork the repo, or contact the maintainer to contribute.
---

## ©️ License

The license will be finalized before public release.
All rights reserved by the author.

---

🎭 *Dive deeper into the labyrinth of your mind. Your journey within Maze of Me awaits.*

