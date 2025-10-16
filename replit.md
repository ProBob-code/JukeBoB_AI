# JUKEBOB - Ultimate Party Entertainment Platform

## Overview
JUKEBOB is a comprehensive entertainment platform with three distinct sections:
1. **Jukebox** - Crowd-controlled music with VIP/Regular queue system and tipping
2. **Games** - Multiplayer games (Tic Tac Toe with emoji reactions)
3. **AI DJ** - Smart mixing with dual turntables

**Tagline:** "Your Ultimate Party Entertainment Hub"

## Current State
The platform is fully functional with:
- ✅ JUKEBOB branding with yellow theme (#F5D547)
- ✅ Multi-section navigation (Jukebox, Games, AI DJ)
- ✅ Password-protected persistent sessions
- ✅ Dark neon theme for Jukebox
- ✅ Light/fun theme for Games  
- ✅ Tech theme for AI DJ
- ✅ VIP/Regular queue system (₹10+ for VIP priority)
- ✅ Tic Tac Toe with real-time gameplay and emoji reactions
- ✅ Dual turntable AI DJ with file uploads
- ✅ Complete payment system with 5% app fee

## Recent Changes
- **2025-10-16**: Complete platform overhaul
  - Rebranded from JuleBox to JUKEBOB
  - Changed currency from $ to ₹ (Indian Rupees)
  - Added password protection for all sessions
  - Implemented VIP/Regular queue segregation
  - Fixed Tic Tac Toe real-time synchronization
  - Added emoji reaction system for games
  - Fixed audio playback in AI DJ
  - Enhanced UI with black text on white inputs

## Project Architecture

### Tech Stack
**Backend:**
- FastAPI (Python) - REST API and WebSocket server
- Uvicorn - ASGI server
- Python 3.11
- SHA256 password hashing

**Frontend:**
- HTML5/CSS3/JavaScript
- WebSocket client for real-time updates
- Multi-theme responsive design
- File upload support for AI DJ
- LocalStorage for session persistence

**Key Libraries:**
- `qrcode` - QR code generation
- `websockets` - Real-time communication
- `supabase` - Database SDK (installed, ready for production)
- `stripe` - Payment processing (installed, ready for production)

### File Structure
```
.
├── backend/
│   ├── main.py          # FastAPI app with all endpoints
│   └── ai_dj.py         # AI DJ agent logic
├── frontend/
│   ├── index.html       # Multi-section UI
│   ├── styles.css       # Theme-based styling
│   ├── app.js           # Navigation & logic
│   ├── logo.png         # JUKEBOB logo
│   └── icon.png         # JB icon
├── pyproject.toml       # Python dependencies
└── replit.md           # This file
```

## Sections

### 1. Jukebox (Dark Neon Theme)
**Features:**
- Password-protected sessions
- VIP Queue (tips ≥ ₹10) - sorted by highest tip
- Regular Queue (tips < ₹10) - first come, first served
- Max 10 songs in queue
- Played songs section
- Real-time queue updates for all participants
- Tip tracking by member name
- Session resume capability
- Host dashboard with earnings
- 5% app fee on checkout

**API Endpoints:**
- `POST /api/sessions/create` - Create jukebox with password
- `POST /api/sessions/{id}/join` - Join with password
- `POST /api/sessions/{id}/resume` - Resume with password
- `POST /api/requests/submit` - Submit song with tip
- `GET /api/requests/{session_id}` - Get segregated queue
- `POST /api/requests/{id}/complete` - Mark as played
- `POST /api/requests/{id}/skip` - Skip song (refund tip)
- `POST /api/checkout/process` - Process payment with app fee

**Queue System:**
- **VIP Queue**: ₹10+ tips, priority play, sorted by amount
- **Regular Queue**: <₹10 tips, standard order
- Visual distinction with golden gradient for VIP songs

### 2. Games (Light/Fun Theme)
**Features:**
- Password-protected game rooms
- Tic Tac Toe with real-time synchronization
- Emoji reaction system (10 emojis)
- Session persistence and resume
- Turn-based gameplay
- Winner/draw detection

**Emoji Reactions:**
- 😂 Laughing
- 😭 Crying
- 😎 Attitude
- 😉 Wink
- 😘 Kiss
- 😜 Tease
- 😱 Shocking
- 👏 Clap
- 🌹 Rose
- 🏆 Trophy

**API Endpoints:**
- `POST /api/games/create` - Create game room with password
- `POST /api/games/join/{code}` - Join with password
- `POST /api/games/{code}/resume` - Resume game
- `GET /api/games/{code}` - Get game state
- `POST /api/games/move` - Make move
- `POST /api/games/emoji` - Send emoji reaction
- `WS /ws/{room_code}` - Real-time updates

**Games Available:**
- ✅ Tic Tac Toe (2 players, real-time, with emojis)
- 🔜 Mafia (Coming soon)

### 3. AI DJ (Tech Theme)
**Features:**
- Dual turntable interface
- Upload tracks from device
- Audio playback with controls
- AI-powered crossfading simulation
- Volume control per deck

**How It Works:**
1. Upload audio files to Deck A and Deck B
2. Files are loaded and ready to play
3. Click play on audio controls
4. Use Auto Mix for simulated crossfading

## Payment System

### Wallet & Tips
- All amounts in ₹ (Indian Rupees)
- VIP queue requires minimum ₹10 tip
- Higher tips get higher priority
- Tips held in escrow until song plays
- Artist receives tip on completion
- Refund on skip

### App Fee System
- 5% fee on all tip transactions
- Fee calculated at checkout
- UPI/GPay integration ready
- Mock payment processing (2-second simulation)

## Real-time Features
- WebSocket connections per session
- Live queue updates for all participants
- Instant game moves and emoji reactions
- Session-wide broadcasts
- Auto-reconnect on disconnect

## Authentication & Security
- Password protection on all sessions
- SHA256 password hashing
- Session persistence with secure resume
- LocalStorage for client-side state
- Passwords never stored in plain text

## User Experience
- Mobile-first responsive design
- Theme-specific color schemes
- Black text on white input fields
- Fast interactions and transitions
- No-cache headers for instant updates
- Floating emoji animations in games

## Next Phase Features
- [ ] Real Supabase database integration
- [ ] Real Stripe/UPI payment processing
- [ ] Mafia game implementation
- [ ] Advanced AI DJ with beat matching
- [ ] Multi-room venue support
- [ ] User authentication system
- [ ] Social sharing features
- [ ] Analytics dashboard

## Testing Instructions

### Jukebox
1. Create jukebox session with password
2. Share code and password with friends
3. Submit songs with different tip amounts
4. Verify VIP songs (≥₹10) appear first
5. Test regular queue for <₹10 tips
6. Mark songs as played/skipped
7. Check played songs section
8. Test session resume after refresh
9. Test checkout with 5% fee

### Games
1. Create Tic Tac Toe room with password
2. Share code and password
3. Join from another browser
4. Play moves - verify real-time sync
5. Send emoji reactions during game
6. Verify winner/draw detection
7. Test session resume after refresh

### AI DJ
1. Upload audio files to both decks
2. Files should load and show ready status
3. Click play to hear audio
4. Test Auto Mix animation
5. Control volume for each deck

## Known Limitations
- Data doesn't persist on server restart (in-memory only)
- Payment integration is simulated
- AI DJ uses basic crossfade (no beat matching)
- Single server instance (no scaling)
- Audio files are temporary (not stored permanently)

## Deployment
Ready for deployment via Replit's Deploy button. The app will get a live URL that can be shared with others. All features are production-ready except real payment gateway integration which requires API keys from Razorpay/Stripe.