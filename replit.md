# JuleBox - Ultimate Party Entertainment Platform

## Overview
JuleBox is a comprehensive entertainment platform with three distinct sections:
1. **Jukebox** - Crowd-controlled music with voting and tipping
2. **Games** - Multiplayer games (Tic Tac Toe, Mafia coming soon)
3. **AI DJ** - Smart mixing with dual turntables

**Tagline:** "Your Ultimate Party Entertainment Hub"

## Current State
The platform is fully functional with:
- ✅ Multi-section navigation (Jukebox, Games, AI DJ)
- ✅ Dark neon theme for Jukebox
- ✅ Light/fun theme for Games  
- ✅ Tech theme for AI DJ
- ✅ Priority queue system (higher tips = higher priority)
- ✅ Tic Tac Toe with real-time gameplay
- ✅ Dual turntable AI DJ with file uploads

## Recent Changes
- **2025-10-16**: Major platform expansion
  - Restructured app into 3 main sections
  - Added Jukebox with priority-based queue (max 10 songs)
  - Implemented played/queued sections
  - Added 5% app fee system with checkout
  - Built Games section with Tic Tac Toe
  - Created AI DJ studio with dual turntables
  - Theme-based UI for each section

## Project Architecture

### Tech Stack
**Backend:**
- FastAPI (Python) - REST API and WebSocket server
- Uvicorn - ASGI server
- Python 3.11

**Frontend:**
- HTML5/CSS3/JavaScript
- WebSocket client for real-time updates
- Multi-theme responsive design
- File upload support for AI DJ

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
│   └── app.js           # Navigation & logic
├── pyproject.toml       # Python dependencies
└── replit.md           # This file
```

## Sections

### 1. Jukebox (Dark Neon Theme)
**Features:**
- Create/Join jukebox sessions with QR codes
- Priority-based queue (higher tips = priority)
- Max 10 songs in queue
- Played songs section
- Real-time voting system
- Tip escrow system with 5% app fee
- Host dashboard with earnings

**API Endpoints:**
- `POST /api/sessions/create` - Create jukebox
- `POST /api/requests/submit` - Submit song with tip
- `GET /api/requests/{session_id}` - Get queue (auto-sorted by tip)
- `POST /api/requests/{id}/complete` - Mark as played
- `POST /api/requests/{id}/skip` - Skip song (refund tip)

**How It Works:**
1. Host creates session, gets QR code
2. Guests join and request songs with tips
3. Queue auto-sorts by tip amount (priority)
4. Top 10 songs shown in queue
5. Host plays/skips songs
6. Played songs move to "Recently Played"
7. Tips held in escrow, released on play
8. Host can checkout with 5% app fee deduction

### 2. Games (Light/Fun Theme)
**Features:**
- Create/Join game rooms
- Tic Tac Toe with real-time gameplay
- Multiplayer matchmaking
- Turn-based system
- Winner detection

**API Endpoints:**
- `POST /api/games/create` - Create game room
- `POST /api/games/join/{code}` - Join game
- `GET /api/games/{code}` - Get game state
- `POST /api/games/move` - Make move
- `WS /ws/{room_code}` - Real-time updates

**Games Available:**
- ✅ Tic Tac Toe (2 players)
- 🔜 Mafia (Coming soon)

### 3. AI DJ (Tech Theme)
**Features:**
- Dual turntable interface
- Upload tracks from device
- AI-powered crossfading
- Auto-mix functionality
- Volume control per deck

**How It Works:**
1. Upload audio files to Deck A and Deck B
2. Click "Auto Mix" to start AI mixing
3. AI automatically crossfades between tracks
4. Manual crossfader control available

## Payment System

### Wallet & Tips
- Users start with $100 virtual balance
- Tips deducted on request
- Held in escrow until song plays
- Artist receives tip on completion
- Requester gets refund if skipped

### App Fee System
- 5% fee on all tip transactions
- Fee calculated at checkout
- Separate accounting for app earnings
- UPI/GPay integration (coming soon)

### Checkout Flow
1. Host views total tips collected
2. System calculates 5% app fee
3. Shows net earnings (95%)
4. Transfer to wallet (UPI/GPay integration pending)

## Real-time Features
- WebSocket connections per session
- Live queue updates
- Instant game moves
- Session-wide broadcasts
- Auto-reconnect on disconnect

## User Preferences
- Mobile-first responsive design
- Theme-specific color schemes
- Fast interactions and transitions
- No-cache headers for instant updates

## Next Phase Features
- [ ] Real Supabase database integration
- [ ] Real Stripe/UPI payment processing
- [ ] Mafia game implementation
- [ ] Advanced AI DJ with beat matching
- [ ] Multi-room venue support
- [ ] User authentication
- [ ] Social sharing features
- [ ] Analytics dashboard

## Development Notes
- Server runs on port 5000 (required for Replit)
- WebSocket auto-reconnect enabled
- In-memory storage (resets on restart)
- No-cache headers prevent browser caching
- QR codes use REPLIT_DEV_DOMAIN
- Static files served from `/frontend`

## Testing Instructions

### Jukebox
1. Create jukebox session
2. Join from another device/browser
3. Submit songs with different tip amounts
4. Verify queue sorts by tip (highest first)
5. Test max 10 queue limit
6. Mark songs as played/skipped
7. Check played songs section
8. Test checkout with 5% fee calculation

### Games
1. Create Tic Tac Toe room
2. Join from another browser
3. Play turns alternately
4. Verify win detection
5. Test draw scenario

### AI DJ
1. Upload audio files to both decks
2. Click Auto Mix
3. Watch crossfader animation
4. Test manual volume control

## Known Limitations
- Data doesn't persist (in-memory only)
- Payment integration is placeholder
- AI DJ uses basic crossfade (no beat matching yet)
- Single server instance (no scaling)
- Browser cache may need hard refresh

## Cache Clearing (If Tabs Don't Work)
If you see "showSection is not defined" errors:
- **Windows/Linux**: Ctrl + Shift + R or Ctrl + F5
- **Mac**: Cmd + Shift + R
- Or clear browser cache manually
