# 🎵 JukeBoB - New User Walkthrough

Welcome to **JukeBoB** - Your Ultimate Party Entertainment Hub! This walkthrough will guide you through the entire project from a new user's perspective.

---

## 📋 What is JukeBoB?

JukeBoB is a comprehensive entertainment platform designed for parties and social gatherings. It combines three exciting features into one:

| Feature | Description |
|---------|-------------|
| **🎵 Jukebox** | Crowd-controlled music with VIP/Regular queue system and tipping |
| **🎮 Games** | Multiplayer games like Tic Tac Toe with real-time sync |
| **🎧 AI DJ** | Smart mixing with dual turntables |

---

## 🏗️ Project Structure

```
JukeBoB_AI/
├── 📂 backend/
│   ├── main.py          # FastAPI server with all API endpoints
│   └── ai_dj.py         # AI DJ agent logic
├── 📂 frontend/
│   ├── index.html       # Multi-section web UI
│   ├── styles.css       # Theme-based styling (3 themes!)
│   ├── app.js           # Navigation & business logic
│   ├── logo.png         # JUKEBOB branding
│   └── icon.png         # JB favicon
├── 📂 flutter_app/       # Cross-platform mobile app
│   └── lib/
│       ├── main.dart    # App entry point
│       ├── config.dart  # API configuration
│       ├── styles.dart  # Theme definitions
│       └── screens/     # UI screens
└── 📄 technical_drawings.html  # Architecture documentation
```

---

## 🎯 Getting Started

### Step 1: Start the Backend Server

The backend is a **FastAPI** Python server. To run it:

```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

> **💡 Tip:** The server will start at `http://localhost:5000` with WebSocket support for real-time features.

### Step 2: Access the Web Frontend

Open your browser and navigate to:
- **Local**: `http://localhost:5000`
- The frontend is served directly by the FastAPI backend

---

## 🎵 Feature 1: Jukebox

The Jukebox allows party hosts to create a music session where guests can request songs with tips.

### For Hosts (DJ/Artist)

#### Create a Session
1. Click **"🎵 Jukebox"** on the home screen
2. Click **"🎤 Host a Jukebox"**
3. Enter:
   - Party Name (e.g., "Saturday Night Party")
   - Your Name (e.g., "DJ Max")
   - Password (to secure your session)
4. Click **Create Jukebox**

You'll get a **QR code** and **session code** to share with guests!

#### Host Dashboard Features
- **Queue View**: See VIP and Regular queues
- **Stats**: Track songs in queue, played count, total tips
- **Controls**: Mark songs as played or skip them
- **Checkout**: Cash out your tips (5% platform fee)

### For Guests

1. Click **"🎉 Join Jukebox"**
2. Enter the session code + password + your name
3. Request songs with optional tips:
   - **₹10+** = VIP Queue (priority!)
   - **< ₹10** = Regular Queue

> **⚠️ Important:** VIP Queue Priority - Songs with ₹10+ tips are played before Regular queue songs. Higher tips get higher priority within VIP!

---

## 🎮 Feature 2: Games Hub

Play multiplayer games with friends in real-time!

### Available Games

| Game | Players | Status |
|------|---------|--------|
| Tic Tac Toe | 2 | ✅ Available |
| Mafia | 5+ | 🔜 Coming Soon |

### How to Play Tic Tac Toe

#### Create a Game Room
1. Navigate to **🎮 Games**
2. Click **"🎯 Create Game Room"**
3. Select **Tic Tac Toe**
4. Set your name and password
5. Share the room code with your opponent

#### Gameplay Features
- **Real-time sync** via WebSockets
- **Scoreboard** tracking wins across rounds
- **Emoji reactions**: 😂 😭 😎 😉 😘 😜 😱 👏 🌹 🏆
- **Play Again** button for rematches
- **Leaderboard** with win streaks

---

## 🎧 Feature 3: AI DJ Studio

Mix tracks like a pro with the dual turntable interface!

### How It Works

1. Upload audio to **Deck A**
2. Upload audio to **Deck B**
3. Use the **Crossfader** to blend tracks
4. Click **"🤖 Auto Mix"** for AI-powered transitions

### Using the AI DJ

1. Navigate to **🎧 AI DJ**
2. Upload audio files to **Deck A** and **Deck B**
3. Use the audio controls to play tracks
4. Click **"🤖 Auto Mix"** for AI-powered crossfading
5. Adjust the crossfader for manual mixing

---

## 💰 Payment System

JukeBoB includes a complete tip and payment system:

| Feature | Details |
|---------|---------|
| Currency | ₹ (Indian Rupees) |
| VIP Threshold | ₹10+ for priority queue |
| Platform Fee | 5% on all tips |
| Payment Status | Simulated (Stripe/UPI ready) |

### Tip Flow

1. Guest requests song with ₹X tip
2. Song added to VIP or Regular queue
3. Host plays the song
4. Host marks as "Played"
5. At checkout: Host receives ₹(X - 5% fee)

---

## 🔐 Security Features

- **Password Protection**: All sessions require passwords
- **SHA256 Hashing**: Passwords never stored in plain text
- **Session Persistence**: Resume sessions after browser refresh
- **LocalStorage**: Client-side state management

---

## 📱 Mobile App (Flutter)

The project includes a cross-platform Flutter app in `flutter_app/` with the same features:

### Running the Flutter App

```bash
cd flutter_app
flutter pub get
flutter run
```

### Key Files

| File | Purpose |
|------|---------|
| `lib/main.dart` | App entry point & providers |
| `lib/config.dart` | Backend API URLs |
| `lib/styles.dart` | Theme definitions |
| `lib/screens/` | UI screens for each feature |

---

## 🎨 Theme System

Each section has its own visual theme:

| Section | Theme | Colors |
|---------|-------|--------|
| Jukebox | Dark Neon | Deep purple, neon accents |
| Games | Light/Fun | Bright, playful colors |
| AI DJ | Tech | Sleek, futuristic gradients |

---

## 🔌 API Endpoints Overview

The backend exposes these key endpoints:

### Session Management
- `POST /api/sessions/create` - Create new jukebox
- `POST /api/sessions/{id}/join` - Join with password
- `POST /api/sessions/{id}/resume` - Resume existing session

### Song Requests
- `POST /api/requests/submit` - Submit song with tip
- `GET /api/requests/{session_id}` - Get queue (VIP + Regular)
- `POST /api/requests/{id}/complete` - Mark as played
- `POST /api/requests/{id}/skip` - Skip song (refund tip)

### Games
- `POST /api/games/create` - Create game room
- `POST /api/games/join/{code}` - Join game
- `POST /api/games/move` - Make a move
- `POST /api/games/emoji` - Send emoji reaction
- `WS /ws/{room_code}` - Real-time updates

### Payments
- `POST /api/checkout/process` - Process tip payout
- `GET /api/revenue` - Get revenue stats

---

## 🔜 Future Roadmap

- [ ] Real database integration (Supabase)
- [ ] Live payment processing (Stripe/Razorpay)
- [ ] Mafia game implementation
- [ ] Advanced AI DJ with beat matching
- [ ] Multi-room venue support
- [ ] User authentication system
- [ ] Social sharing features
- [ ] Analytics dashboard

---

## ⚠️ Known Limitations

- Data doesn't persist on server restart (in-memory only)
- Payment integration is simulated
- AI DJ uses basic crossfade (no beat matching)
- Single server instance (no scaling)
- Audio files are temporary (not stored permanently)

---

## 📚 Additional Resources

- **Technical Architecture**: See `technical_drawings.html` for detailed system diagrams
- **Executive Presentation**: See `JukeBoB_Executive_Presentation.pptx`
- **Backend Code**: `backend/main.py` - FastAPI implementation
- **Frontend Code**: `frontend/app.js` - JavaScript logic

---

## 🚀 Deployment

Ready for deployment via Replit's Deploy button. The app will get a live URL that can be shared with others. All features are production-ready except real payment gateway integration which requires API keys from Razorpay/Stripe.

---

> **📝 Note:** This project uses **in-memory storage** by default. Data won't persist after server restart. For production, integrate Supabase as documented in the codebase.

---

**Happy Partying! 🎉**

*Version 1.0 • December 2025*
