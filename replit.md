# Jukebox AI - Party Music Platform

## Overview
Jukebox AI is an interactive, AI-powered jukebox platform built for artists, DJs, event hosts, and party crowds. It transforms any gathering into a collaborative music experience where everyone becomes part of the performance.

**Tagline:** "Let the crowd choose, the artist groove, and the AI mix the mood."

## Current State - MVP
The MVP is fully functional with the following features:
- ✅ Party session creation with QR codes
- ✅ Real-time song requests and voting
- ✅ Live WebSocket updates across all devices
- ✅ Digital wallet and tipping system
- ✅ AI DJ agent with playlist management
- ✅ Artist dashboard with earnings tracking
- ✅ Crowd playlist mode

## Recent Changes
- **2025-10-16**: Initial MVP implementation
  - Created FastAPI backend with WebSocket support
  - Built responsive web frontend with gradient UI
  - Implemented voting mechanism with 1-minute windows
  - Added AI DJ agent with auto-mixing capabilities
  - Set up QR code generation for easy party joining
  - Configured workflow for development server

## Project Architecture

### Tech Stack
**Backend:**
- FastAPI (Python) - REST API and WebSocket server
- Uvicorn - ASGI server
- Python 3.11

**Frontend:**
- HTML5/CSS3/JavaScript
- WebSocket client for real-time updates
- Responsive mobile-first design

**Key Libraries:**
- `qrcode` - QR code generation
- `websockets` - Real-time communication
- `supabase` - Database SDK (installed, not yet integrated)
- `stripe` - Payment processing (installed, not yet integrated)

### File Structure
```
.
├── backend/
│   ├── main.py          # FastAPI app with all endpoints
│   └── ai_dj.py         # AI DJ agent logic
├── frontend/
│   ├── index.html       # Main UI
│   ├── styles.css       # Styling
│   └── app.js           # Frontend logic
├── pyproject.toml       # Python dependencies
└── replit.md           # This file
```

## Key Features

### 1. Party Sessions
- Create sessions with unique 8-character codes
- Generate QR codes for easy joining
- Real-time participant updates

### 2. Song Requests & Voting
- Anyone can request songs
- Automatic voting when 2+ requests pending
- 60-second voting windows
- Real-time vote tallying

### 3. Digital Wallet & Tipping
- Virtual wallet system for each user
- Tip functionality for song requests
- Artist earnings dashboard
- Future: Real Stripe integration

### 4. AI DJ Agent
- Automatic playlist management
- Crowd mood analysis
- Song suggestion algorithm
- Auto-transition logic (basic fade)

### 5. Real-time Updates
- WebSocket connections per session
- Live vote updates
- Instant request notifications
- Session-wide broadcasts

## API Endpoints

### Sessions
- `POST /api/sessions/create` - Create new party
- `GET /api/sessions/{session_id}` - Get session details

### Song Requests
- `POST /api/requests/submit` - Submit song request
- `GET /api/requests/{session_id}` - Get all requests
- `POST /api/requests/vote` - Vote for a song
- `POST /api/requests/{request_id}/complete` - Mark as played
- `POST /api/requests/{request_id}/skip` - Skip song

### AI DJ
- `POST /api/dj/{session_id}/enable` - Enable AI DJ mode
- `GET /api/dj/{session_id}/playlist` - Get playlist status
- `POST /api/dj/{session_id}/next` - Play next track

### Wallet
- `GET /api/wallet/{user_id}` - Get wallet balance
- `POST /api/requests/tip` - Tip a request

### WebSocket
- `WS /ws/{session_id}` - Real-time updates

## User Preferences
- Mobile-first responsive design
- Real-time updates essential
- Clean, party-ready UI with gradient backgrounds
- Fast interactions (voting, tipping)

## Next Phase Features
- [ ] Database persistence (Supabase/PostgreSQL)
- [ ] Real Stripe payment integration
- [ ] Advanced AI DJ with audio analysis
- [ ] Multi-room support for venues
- [ ] Artist profiles and analytics
- [ ] Social sharing and playlist export
- [ ] Hook detection and smart transitions
- [ ] Beat/key matching for seamless mixing

## Development Notes
- Server runs on port 5000 (required for Replit)
- WebSocket connections auto-reconnect
- In-memory storage (resets on restart)
- QR codes use REPLIT_DEV_DOMAIN for URLs
- Static files served from `/frontend`

## Testing
To test the app:
1. Create a party session
2. Copy session code or scan QR
3. Join from another browser/device
4. Submit song requests
5. Vote when voting opens
6. Test tipping functionality
7. Artist marks songs as played/skipped

## Known Limitations
- Data doesn't persist (in-memory only)
- No actual payment processing yet
- Basic AI DJ (no audio file processing)
- Single server instance (no scaling)
