// Global state
let currentSession = null;
let currentUser = null;
let hostToken = null;       // auth token for host-only jukebox actions
let ws = null;
let currentGame = null;
let deckA = null;
let deckB = null;

// Escape user-supplied text before inserting into innerHTML (XSS protection).
function escapeHtml(str) {
    return String(str == null ? '' : str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// ============== NAVIGATION ==============

function showSection(sectionName) {
    // Hide all screens
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });

    // Show selected section
    const section = document.getElementById(`${sectionName}-section`);
    if (section) {
        section.classList.add('active');

        // Show the home sub-screen of that section
        const subScreens = section.querySelectorAll('.sub-screen');
        subScreens.forEach(s => s.classList.remove('active'));

        const homeScreen = section.querySelector('.sub-screen');
        if (homeScreen) {
            homeScreen.classList.add('active');
        }
    }
}

function backToHome() {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById('main-home').classList.add('active');
}

function showJukeboxScreen(screenName) {
    const parent = document.getElementById('jukebox-section');
    parent.querySelectorAll('.sub-screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(screenName).classList.add('active');
}

function showGamesScreen(screenName) {
    const parent = document.getElementById('games-section');
    parent.querySelectorAll('.sub-screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(screenName).classList.add('active');
}

// ============== JUKEBOX ==============

async function createJukebox(event) {
    event.preventDefault();

    const partyName = document.getElementById('jukebox-name').value;
    const hostName = document.getElementById('host-name').value;
    const password = document.getElementById('jukebox-password').value;

    try {
        const response = await fetch('/api/sessions/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: partyName,
                artist_id: hostName,
                password: password
            })
        });

        const data = await response.json();
        currentSession = data.session_id;
        hostToken = data.host_token;
        currentUser = { name: hostName, role: 'host' };

        document.getElementById('host-jukebox-name').textContent = partyName;
        document.getElementById('jukebox-code-display').textContent = data.session_id;
        document.getElementById('jukebox-qr').src = 'data:image/png;base64,' + data.qr_code;

        connectWebSocket(data.session_id);
        showJukeboxScreen('host-dashboard');
        loadHostRequests();
    } catch (error) {
        alert('Error creating jukebox: ' + error.message);
    }
}

async function joinJukebox(event) {
    event.preventDefault();

    const sessionCode = document.getElementById('jukebox-code').value.toUpperCase();
    const guestName = document.getElementById('guest-name-jukebox').value;
    const password = document.getElementById('jukebox-join-password').value;

    try {
        const response = await fetch(`/api/sessions/${sessionCode}/join`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                guest_name: guestName,
                password: password
            })
        });
        if (!response.ok) throw new Error('Session not found or password incorrect');

        const session = await response.json();
        currentSession = sessionCode;
        currentUser = { name: guestName, role: 'guest' };

        document.getElementById('guest-jukebox-name').textContent = session.name;

        connectWebSocket(sessionCode);
        showJukeboxScreen('guest-jukebox');
        loadGuestRequests();
    } catch (error) {
        alert('Error joining jukebox: ' + error.message);
    }
}

function connectWebSocket(sessionId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${sessionId}`;

    ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    ws.onclose = () => {
        setTimeout(() => connectWebSocket(sessionId), 3000);
    };
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'new_request':
        case 'request_completed':
        case 'request_skipped':
        case 'queue_update':
        case 'tip_added':
            refreshJukebox();
            break;
        case 'game_move':
            if (currentGame && data.room) {
                currentGame.board = data.room.board;
                currentGame.currentTurn = data.room.current_turn;
                currentGame.scores = data.room.scores;
                currentGame.games_played = data.room.games_played;
                currentGame.leaderboard = data.room.leaderboard;
                renderTicTacToe();
                updateScoreboard(data.room);
                updateLeaderboard(data.room);
                checkGameEnd();
            }
            break;
        case 'game_restarted':
            if (currentGame && data.room) {
                currentGame.board = data.room.board;
                currentGame.currentTurn = data.room.current_turn;
                currentGame.scores = data.room.scores;
                currentGame.games_played = data.room.games_played;
                currentGame.leaderboard = data.room.leaderboard;

                // Update starting player if it changed
                if (data.starting_player) {
                    currentGame.startingPlayer = data.starting_player;
                    // Swap player symbols if needed
                    if (data.starting_player === 'O' && currentGame.yourSymbol === 'X' && currentGame.player1 === currentGame.playerName) {
                        currentGame.yourSymbol = 'O';
                    } else if (data.starting_player === 'X' && currentGame.yourSymbol === 'O' && currentGame.player1 === currentGame.playerName) {
                        currentGame.yourSymbol = 'X';
                    }
                }

                renderTicTacToe();
                updateScoreboard(data.room);
                updateLeaderboard(data.room);

                // Hide restart button and clear result
                document.getElementById('restart-container').style.display = 'none';
                document.getElementById('ttt-result').textContent = '';
                document.getElementById('restart-status').textContent = '';
            }
            break;
        case 'restart_requested':
            if (currentGame) {
                const status = document.getElementById('restart-status');
                if (status) {
                    status.textContent = `${data.requesting_player} wants to play again...`;
                }
            }
            break;
        case 'player_joined':
            if (currentGame && data.room) {
                currentGame.player2 = data.room.player2;
                updateScoreboard(data.room);
                updateLeaderboard(data.room);
            }
            break;
        case 'emoji_reaction':
            showFloatingEmoji(data.player_name, data.emoji);
            break;
    }
}

async function submitSongRequest(event) {
    event.preventDefault();

    const songName = document.getElementById('song-name').value;
    const songArtist = document.getElementById('song-artist').value;
    const tipAmount = parseFloat(document.getElementById('tip-amount').value) || 0;

    try {
        const response = await fetch('/api/requests/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                song_name: songName,
                artist: songArtist,
                requester_name: currentUser.name,
                session_id: currentSession,
                tip_amount: tipAmount
            })
        });

        await response.json();
        closeRequestForm();
        event.target.reset();
        refreshJukebox();
    } catch (error) {
        alert('Error submitting request: ' + error.message);
    }
}

async function completeRequest(requestId) {
    try {
        const res = await fetch(`/api/requests/${requestId}/complete?session_id=${currentSession}&host_token=${encodeURIComponent(hostToken || '')}`, {
            method: 'POST'
        });
        if (!res.ok) throw new Error('Not authorized or request not found');
        refreshJukebox();
    } catch (error) {
        alert('Error completing request: ' + error.message);
    }
}

async function skipRequest(requestId) {
    try {
        const res = await fetch(`/api/requests/${requestId}/skip?session_id=${currentSession}&host_token=${encodeURIComponent(hostToken || '')}`, {
            method: 'POST'
        });
        if (!res.ok) throw new Error('Not authorized or request not found');
        refreshJukebox();
    } catch (error) {
        alert('Error skipping request: ' + error.message);
    }
}

async function loadHostRequests() {
    try {
        const response = await fetch(`/api/requests/${currentSession}`);
        const requests = await response.json();

        // Sort by tip amount (priority)
        const queued = requests.filter(r => r.status === 'queued')
            .sort((a, b) => b.tip_amount - a.tip_amount)
            .slice(0, 10);
        const played = requests.filter(r => r.status === 'completed').slice(0, 10);

        // Earnings = tips from songs that actually played (matches backend payout).
        const totalTips = requests
            .filter(r => r.status === 'completed')
            .reduce((sum, r) => sum + r.tip_amount, 0);

        document.getElementById('queue-count').textContent = queued.length;
        document.getElementById('played-count').textContent = played.length;
        document.getElementById('host-tips').textContent = '₹' + totalTips.toFixed(2);

        renderQueue('host-queue', queued, true);
        renderPlayed('host-played', played);
    } catch (error) {
        console.error('Error loading requests:', error);
    }
}

async function loadGuestRequests() {
    try {
        const response = await fetch(`/api/requests/${currentSession}`);
        const requests = await response.json();

        const queued = requests.filter(r => r.status === 'queued')
            .sort((a, b) => b.tip_amount - a.tip_amount)
            .slice(0, 10);
        const played = requests.filter(r => r.status === 'completed').slice(0, 10);

        renderQueue('guest-queue', queued, false);
        renderPlayed('guest-played', played);
    } catch (error) {
        console.error('Error loading requests:', error);
    }
}

function renderQueue(containerId, requests, isHost) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    if (requests.length === 0) {
        container.innerHTML = '<p style="color: rgba(255,255,255,0.5);">No songs in queue</p>';
        return;
    }

    // Separate VIP and Regular songs
    const vipSongs = requests.filter(r => r.tip_amount >= 10);
    const regularSongs = requests.filter(r => r.tip_amount < 10);

    // Add VIP Queue section if there are VIP songs
    if (vipSongs.length > 0) {
        const vipHeader = document.createElement('div');
        vipHeader.className = 'queue-section-header vip-header';
        vipHeader.innerHTML = `
            <h3>👑 VIP Queue</h3>
            <p class="vip-note">Songs with tips ₹10 or more get priority</p>
        `;
        container.appendChild(vipHeader);

        vipSongs.forEach((req, index) => {
            const card = document.createElement('div');
            card.className = 'request-card vip-card';
            card.innerHTML = `
                <div class="vip-indicator">👑</div>
                <div class="request-info">
                    <h4>#${index + 1} ${escapeHtml(req.song_name)}</h4>
                    <p>${escapeHtml(req.artist)} • ${escapeHtml(req.requester_name)}</p>
                    <p class="tip-amount vip-tip">💰 VIP Tip: ₹${req.tip_amount.toFixed(2)}</p>
                </div>
                ${isHost ? `
                    <div class="request-actions">
                        <button class="complete-btn" onclick="completeRequest('${req.id}')">✓</button>
                        <button class="skip-btn" onclick="skipRequest('${req.id}')">✗</button>
                    </div>
                ` : ''}
            `;
            container.appendChild(card);
        });
    }

    // Add Regular Queue section if there are regular songs
    if (regularSongs.length > 0) {
        const regularHeader = document.createElement('div');
        regularHeader.className = 'queue-section-header regular-header';
        regularHeader.innerHTML = `
            <h3>🎵 Regular Queue</h3>
            <p class="regular-note">Tip ₹10 or more to jump to VIP queue</p>
        `;
        container.appendChild(regularHeader);

        regularSongs.forEach((req, index) => {
            const card = document.createElement('div');
            card.className = 'request-card regular-card';
            card.innerHTML = `
                <div class="request-info">
                    <h4>#${vipSongs.length + index + 1} ${escapeHtml(req.song_name)}</h4>
                    <p>${escapeHtml(req.artist)} • ${escapeHtml(req.requester_name)}</p>
                    <p class="tip-amount">💰 Tip: ₹${req.tip_amount.toFixed(2)}</p>
                </div>
                ${isHost ? `
                    <div class="request-actions">
                        <button class="complete-btn" onclick="completeRequest('${req.id}')">✓</button>
                        <button class="skip-btn" onclick="skipRequest('${req.id}')">✗</button>
                    </div>
                ` : ''}
            `;
            container.appendChild(card);
        });
    }
}

function renderPlayed(containerId, requests) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    if (requests.length === 0) {
        container.innerHTML = '<p style="color: rgba(255,255,255,0.5);">No songs played yet</p>';
        return;
    }

    requests.forEach(req => {
        const card = document.createElement('div');
        card.className = 'request-card';
        card.innerHTML = `
            <div class="request-info">
                <h4>${escapeHtml(req.song_name)}</h4>
                <p>${escapeHtml(req.artist)} • ${escapeHtml(req.requester_name)}</p>
            </div>
        `;
        container.appendChild(card);
    });
}

function refreshJukebox() {
    if (currentUser && currentUser.role === 'host') {
        loadHostRequests();
    } else {
        loadGuestRequests();
    }
}

function showRequestForm() {
    document.getElementById('request-modal').classList.add('active');
}

function closeRequestForm() {
    document.getElementById('request-modal').classList.remove('active');
}

function showCheckout() {
    document.getElementById('checkout-modal').classList.add('active');
    const totalTips = parseFloat(document.getElementById('host-tips').textContent.replace('₹', '')) || 0;
    const appFee = totalTips * 0.05;
    const netEarnings = totalTips * 0.95;

    // Show checkout info
    document.getElementById('checkout-info').innerHTML = `
        <p>Total Tips Collected: <strong>₹${totalTips.toFixed(2)}</strong></p>
        <p>App Fee (5%): <strong>₹${appFee.toFixed(2)}</strong></p>
        <p>Your Earnings: <strong>₹${netEarnings.toFixed(2)}</strong></p>
        
        <div class="payment-methods" style="margin: 20px 0;">
            <h4>Select Payment Method:</h4>
            <button class="btn btn-primary" onclick="processPayment('upi')" style="margin: 5px;">
                <i class="fas fa-rupee-sign"></i> UPI Payment
            </button>
            <button class="btn btn-primary" onclick="processPayment('gpay')" style="margin: 5px;">
                <i class="fab fa-google"></i> Google Pay
            </button>
        </div>
        
        <div id="payment-status" style="display: none; margin-top: 20px;">
            <div class="loader"></div>
            <p>Processing payment...</p>
        </div>
        
        <div id="payment-result" style="display: none; margin-top: 20px;"></div>
    `;
}

function closeCheckout() {
    document.getElementById('checkout-modal').classList.remove('active');
}

async function processPayment(method) {
    const statusDiv = document.getElementById('payment-status');
    const resultDiv = document.getElementById('payment-result');

    statusDiv.style.display = 'block';
    resultDiv.style.display = 'none';

    try {
        const response = await fetch('/api/checkout/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSession,
                payment_method: method,
                upi_id: method === 'upi' ? 'artist@upi' : null,
                host_token: hostToken || ''
            })
        });

        const result = await response.json();

        statusDiv.style.display = 'none';
        resultDiv.style.display = 'block';

        if (result.success) {
            resultDiv.innerHTML = `
                <div class="success-message" style="color: #4caf50;">
                    <i class="fas fa-check-circle"></i>
                    <h3>Payment Successful!</h3>
                    <p>Transaction ID: ${result.transaction_id}</p>
                    <p>Amount Received: ₹${result.net_amount.toFixed(2)}</p>
                    <p>App Fee: ₹${result.app_fee.toFixed(2)}</p>
                    <button class="btn btn-success" onclick="closeCheckout()">Done</button>
                </div>
            `;
            // Update host tips display
            document.getElementById('host-tips').textContent = '₹0.00';
        } else {
            resultDiv.innerHTML = `
                <div class="error-message" style="color: #f44336;">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>${result.message || 'Payment failed. Please try again.'}</p>
                    <button class="btn btn-secondary" onclick="closeCheckout()">Close</button>
                </div>
            `;
        }
    } catch (error) {
        statusDiv.style.display = 'none';
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = `
            <div class="error-message" style="color: #f44336;">
                <i class="fas fa-exclamation-circle"></i>
                <p>Network error. Please try again.</p>
                <button class="btn btn-secondary" onclick="closeCheckout()">Close</button>
            </div>
        `;
    }
}

function endJukebox() {
    if (confirm('End this jukebox session?')) {
        if (ws) ws.close();
        currentSession = null;
        currentUser = null;
        showJukeboxScreen('jukebox-home');
    }
}

function leaveJukebox() {
    if (ws) ws.close();
    currentSession = null;
    currentUser = null;
    showJukeboxScreen('jukebox-home');
}

// Resume Jukebox Session
async function resumeJukebox(event) {
    event.preventDefault();

    const sessionCode = document.getElementById('resume-jukebox-code').value.toUpperCase();
    const password = document.getElementById('resume-jukebox-password').value;

    try {
        const response = await fetch(`/api/sessions/${sessionCode}/resume`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: password })
        });

        if (!response.ok) throw new Error('Session not found or password incorrect');

        const data = await response.json();
        currentSession = sessionCode;
        hostToken = data.host_token;
        currentUser = data.user_role;

        if (data.user_role.role === 'host') {
            document.getElementById('host-jukebox-name').textContent = data.session.name;
            document.getElementById('jukebox-code-display').textContent = sessionCode;
            document.getElementById('jukebox-qr').src = 'data:image/png;base64,' + data.qr_code;
            showJukeboxScreen('host-dashboard');
            loadHostRequests();
        } else {
            document.getElementById('guest-jukebox-name').textContent = data.session.name;
            showJukeboxScreen('guest-jukebox');
            loadGuestRequests();
        }

        connectWebSocket(sessionCode);
    } catch (error) {
        alert('Error resuming session: ' + error.message);
    }
}

// ============== GAMES ==============

async function createGameRoom(event) {
    event.preventDefault();

    const gameType = document.getElementById('game-type').value;
    const hostName = document.getElementById('game-host-name').value;
    const password = document.getElementById('game-password').value;

    // Store player name for later use
    localStorage.setItem('playerName', hostName);
    currentUser = { name: hostName, role: 'host' };

    try {
        const response = await fetch('/api/games/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                game_type: gameType,
                player_name: hostName,
                password: password
            })
        });

        const data = await response.json();
        currentGame = {
            code: data.room_code,
            type: gameType,
            player1: hostName,
            player2: null,
            board: Array(9).fill(null),
            currentTurn: 'X',
            yourSymbol: 'X',
            playerName: hostName,
            playerToken: data.player_token,
            scores: data.room.scores || { 'X': 0, 'O': 0 },
            games_played: data.room.games_played || 0,
            leaderboard: data.room.leaderboard || {}
        };
        localStorage.setItem(`gameToken_${data.room_code}`, data.player_token);

        // Connect WebSocket for real-time updates
        connectGameWebSocket(data.room_code);

        document.getElementById('ttt-room-code').textContent = data.room_code;
        renderTicTacToe();
        updateScoreboard(data.room);
        updateLeaderboard(data.room);
        showGamesScreen('tictactoe-game');
    } catch (error) {
        alert('Error creating game room: ' + error.message);
    }
}

async function joinGameRoom(event) {
    event.preventDefault();

    const gameCode = document.getElementById('game-code').value.toUpperCase();
    const playerName = document.getElementById('game-player-name').value;
    const password = document.getElementById('game-join-password').value;

    // Store player name for later use
    localStorage.setItem('playerName', playerName);
    currentUser = { name: playerName, role: 'guest' };

    try {
        const response = await fetch(`/api/games/join/${gameCode}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                player_name: playerName,
                password: password
            })
        });

        if (!response.ok) throw new Error('Game not found or password incorrect');

        const data = await response.json();
        currentGame = {
            code: gameCode,
            type: 'tictactoe',
            player1: data.room.player1,
            player2: playerName,
            board: data.room.board,
            currentTurn: data.room.current_turn,
            yourSymbol: 'O',
            playerName: playerName,
            playerToken: data.player_token,
            scores: data.room.scores || { 'X': 0, 'O': 0 },
            games_played: data.room.games_played || 0,
            leaderboard: data.room.leaderboard || {}
        };
        localStorage.setItem(`gameToken_${gameCode}`, data.player_token);

        // Connect WebSocket for real-time updates
        connectGameWebSocket(gameCode);

        document.getElementById('ttt-room-code').textContent = gameCode;
        renderTicTacToe();
        updateScoreboard(data.room);
        updateLeaderboard(data.room);
        showGamesScreen('tictactoe-game');
    } catch (error) {
        alert('Error joining game: ' + error.message);
    }
}

// Resume game function
async function resumeGame(event) {
    event.preventDefault();

    const gameCode = document.getElementById('resume-game-code').value.toUpperCase();
    const password = document.getElementById('resume-game-password').value;

    try {
        const response = await fetch(`/api/games/${gameCode}`, {
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) throw new Error('Game not found');

        const room = await response.json();

        // Determine which player they are based on stored session
        const playerName = localStorage.getItem('playerName');
        const yourSymbol = room.player1 === playerName ? 'X' : 'O';

        currentGame = {
            code: gameCode,
            type: room.type,
            player1: room.player1,
            player2: room.player2,
            board: room.board,
            currentTurn: room.current_turn,
            yourSymbol: yourSymbol,
            playerName: playerName,
            playerToken: localStorage.getItem(`gameToken_${gameCode}`) || '',
            scores: room.scores || { 'X': 0, 'O': 0 },
            games_played: room.games_played || 0,
            leaderboard: room.leaderboard || {}
        };

        connectGameWebSocket(gameCode);

        document.getElementById('ttt-room-code').textContent = gameCode;
        renderTicTacToe();
        showGamesScreen('tictactoe-game');
    } catch (error) {
        alert('Error resuming game: ' + error.message);
    }
}

// WebSocket for games
function connectGameWebSocket(roomCode) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${roomCode}`;

    if (ws) ws.close();
    ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    ws.onclose = () => {
        setTimeout(() => connectGameWebSocket(roomCode), 3000);
    };
}

function renderTicTacToe() {
    const board = document.getElementById('tictactoe-board');
    board.innerHTML = '';

    for (let i = 0; i < 9; i++) {
        const cell = document.createElement('div');
        cell.className = 'ttt-cell';
        cell.textContent = currentGame.board[i] || '';
        if (currentGame.board[i]) cell.classList.add('taken');
        cell.onclick = () => makeMove(i);
        board.appendChild(cell);
    }

    updateTurnInfo();
}

async function makeMove(index) {
    if (currentGame.board[index] || checkWinner()) return;
    if (currentGame.currentTurn !== currentGame.yourSymbol) return;

    // Get the player name from currentGame or localStorage
    const playerName = currentGame.playerName || currentUser?.name || localStorage.getItem('playerName');

    if (!playerName) {
        alert('Player name not found. Please refresh and try again.');
        return;
    }

    try {
        const response = await fetch('/api/games/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                room_code: currentGame.code,
                player_name: playerName,
                move: index,
                player_token: currentGame.playerToken || localStorage.getItem(`gameToken_${currentGame.code}`) || ''
            })
        });

        if (!response.ok) throw new Error('Invalid move');

        const data = await response.json();
        currentGame.board = data.room.board;
        currentGame.currentTurn = data.room.current_turn;

        renderTicTacToe();
        checkGameEnd();
    } catch (error) {
        alert('Error making move: ' + error.message);
    }
}

function updateTurnInfo() {
    const info = document.getElementById('ttt-turn-info');
    if (currentGame.currentTurn === currentGame.yourSymbol) {
        info.textContent = `Your turn (${currentGame.yourSymbol})`;
        info.style.color = '#48bb78';
    } else {
        info.textContent = `Opponent's turn (${currentGame.currentTurn})`;
        info.style.color = '#f56565';
    }
}

function checkWinner() {
    const wins = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],
        [0, 3, 6], [1, 4, 7], [2, 5, 8],
        [0, 4, 8], [2, 4, 6]
    ];

    for (let combo of wins) {
        const [a, b, c] = combo;
        if (currentGame.board[a] &&
            currentGame.board[a] === currentGame.board[b] &&
            currentGame.board[a] === currentGame.board[c]) {
            return currentGame.board[a];
        }
    }
    return null;
}

function leaveGame() {
    currentGame = null;
    showGamesScreen('games-home');
}

// Emoji Reaction Functions
async function sendEmoji(emoji) {
    if (!currentGame || !currentGame.code) {
        alert('No active game');
        return;
    }

    const playerName = currentGame.playerName || currentUser?.name || localStorage.getItem('playerName');

    if (!playerName) {
        alert('Player name not found');
        return;
    }

    try {
        const response = await fetch('/api/games/emoji', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                room_code: currentGame.code,
                player_name: playerName,
                emoji: emoji,
                player_token: currentGame.playerToken || localStorage.getItem(`gameToken_${currentGame.code}`) || ''
            })
        });

        if (!response.ok) throw new Error('Failed to send emoji');
    } catch (error) {
        console.error('Error sending emoji:', error);
    }
}

function showFloatingEmoji(playerName, emoji) {
    const container = document.getElementById('emoji-reactions-container');
    if (!container) return;

    const emojiElement = document.createElement('div');
    emojiElement.className = 'floating-emoji';

    // Random position in the middle area of the screen
    const randomX = Math.random() * 60 + 20; // Between 20% and 80%
    const randomY = Math.random() * 30 + 50; // Between 50% and 80%

    emojiElement.style.left = `${randomX}%`;
    emojiElement.style.top = `${randomY}%`;

    emojiElement.innerHTML = `
        <span>${escapeHtml(emoji)}</span>
        <span class="emoji-sender">${escapeHtml(playerName)}</span>
    `;

    container.appendChild(emojiElement);

    // Remove after animation completes
    setTimeout(() => {
        container.removeChild(emojiElement);
    }, 3000);
}

function checkGameEnd() {
    const winner = checkWinner();
    if (winner) {
        document.getElementById('ttt-result').textContent =
            winner === currentGame.yourSymbol ? 'You Won! 🎉' : 'You Lost!';
        document.getElementById('restart-container').style.display = 'block';
        animateScoreChange(winner);
    } else if (currentGame.board.every(cell => cell)) {
        document.getElementById('ttt-result').textContent = "It's a Draw!";
        document.getElementById('restart-container').style.display = 'block';
    }
}

// New functions for scoreboard and leaderboard
function updateScoreboard(room) {
    if (!room) return;

    // Update player names
    const player1Name = document.getElementById('player1-name');
    const player2Name = document.getElementById('player2-name');
    if (player1Name) player1Name.textContent = room.player1 || 'Player X';
    if (player2Name) player2Name.textContent = room.player2 || 'Waiting...';

    // Update scores
    const scoreX = document.getElementById('score-x');
    const scoreO = document.getElementById('score-o');
    if (scoreX && room.scores) scoreX.textContent = room.scores.X || 0;
    if (scoreO && room.scores) scoreO.textContent = room.scores.O || 0;

    // Update round number
    const roundNumber = document.getElementById('round-number');
    if (roundNumber) roundNumber.textContent = room.games_played || 0;
}

function updateLeaderboard(room) {
    if (!room || !room.leaderboard) return;

    // Update player 1 leaderboard
    const player1Data = room.leaderboard[room.player1];
    if (player1Data) {
        const lb1Name = document.querySelector('#lb-player1 .lb-name');
        if (lb1Name) lb1Name.textContent = room.player1;

        document.getElementById('lb-p1-wins').textContent = player1Data.wins || 0;
        document.getElementById('lb-p1-games').textContent = player1Data.games || 0;

        const winPercent = player1Data.games > 0
            ? Math.round((player1Data.wins / player1Data.games) * 100)
            : 0;
        document.getElementById('lb-p1-percent').textContent = winPercent + '%';

        const streakEl = document.getElementById('lb-p1-streak');
        if (streakEl) {
            streakEl.textContent = player1Data.streak || 0;
            if (player1Data.streak > 0) {
                streakEl.classList.add('streak-active');
            } else {
                streakEl.classList.remove('streak-active');
            }
        }
    }

    // Update player 2 leaderboard
    if (room.player2) {
        const player2Data = room.leaderboard[room.player2];
        if (player2Data) {
            const lb2Name = document.querySelector('#lb-player2 .lb-name');
            if (lb2Name) lb2Name.textContent = room.player2;

            document.getElementById('lb-p2-wins').textContent = player2Data.wins || 0;
            document.getElementById('lb-p2-games').textContent = player2Data.games || 0;

            const winPercent = player2Data.games > 0
                ? Math.round((player2Data.wins / player2Data.games) * 100)
                : 0;
            document.getElementById('lb-p2-percent').textContent = winPercent + '%';

            const streakEl = document.getElementById('lb-p2-streak');
            if (streakEl) {
                streakEl.textContent = player2Data.streak || 0;
                if (player2Data.streak > 0) {
                    streakEl.classList.add('streak-active');
                } else {
                    streakEl.classList.remove('streak-active');
                }
            }
        }
    }
}

async function requestRestart() {
    if (!currentGame || !currentGame.code) {
        alert('No active game');
        return;
    }

    const playerName = currentGame.playerName || currentUser?.name || localStorage.getItem('playerName');
    if (!playerName) {
        alert('Player name not found');
        return;
    }

    try {
        const response = await fetch('/api/games/restart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                room_code: currentGame.code,
                player_name: playerName,
                player_token: currentGame.playerToken || localStorage.getItem(`gameToken_${currentGame.code}`) || ''
            })
        });

        if (!response.ok) throw new Error('Failed to restart game');

        const data = await response.json();
        if (data.restarted) {
            document.getElementById('restart-status').textContent = 'Game restarted!';
        } else if (data.pending) {
            document.getElementById('restart-status').textContent = 'Waiting for other player...';
        }
    } catch (error) {
        alert('Error restarting game: ' + error.message);
    }
}

function animateScoreChange(winner) {
    const scoreEl = winner === 'X'
        ? document.getElementById('score-x')
        : document.getElementById('score-o');

    if (scoreEl) {
        scoreEl.classList.add('score-change');
        setTimeout(() => {
            scoreEl.classList.remove('score-change');
        }, 1000);
    }
}

// ============== ENHANCED AI DJ ==============

// Audio context and state
let audioContext = null;
let analyserA = null;
let analyserB = null;
let sourceA = null;
let sourceB = null;
let playlist = [];
let autoplayEnabled = false;
let isMixing = false;
let activeEffects = { lowpass: false, echo: false };

// Initialize Audio Context (call on first user interaction)
function initAudioContext() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    return audioContext;
}

// Enhanced Track Loading with Waveform Generation
async function loadTrack(deck, input) {
    const file = input.files[0];
    if (!file) return;

    const url = URL.createObjectURL(file);
    const player = document.getElementById(`deck-${deck}-player`);
    const nameEl = document.querySelector(`#deck-${deck}-info .track-name`);
    const waveformContainer = document.getElementById(`waveform-${deck}`);

    // Update UI
    nameEl.textContent = file.name.replace(/\.[^/.]+$/, ""); // Remove extension
    waveformContainer.innerHTML = '<div class="waveform-placeholder">Loading waveform...</div>';

    // Set player source
    player.src = url;
    player.load();

    // Store deck information
    if (deck === 'a') {
        deckA = { file, url, name: file.name };
    } else {
        deckB = { file, url, name: file.name };
    }

    // Setup time update listener
    player.ontimeupdate = () => updateTimeDisplay(deck);
    player.onended = () => handleTrackEnd(deck);

    // Generate waveform
    try {
        await generateWaveform(file, deck);
        showDJToast(`Track loaded on Deck ${deck.toUpperCase()}`, 'success');
    } catch (error) {
        console.error('Error generating waveform:', error);
        waveformContainer.innerHTML = '<div class="waveform-placeholder">Ready to play</div>';
    }
}

// Generate Waveform using Web Audio API
async function generateWaveform(file, deck) {
    const ctx = initAudioContext();
    const arrayBuffer = await file.arrayBuffer();
    const audioBuffer = await ctx.decodeAudioData(arrayBuffer);

    const rawData = audioBuffer.getChannelData(0);
    const samples = 150; // Number of bars
    const blockSize = Math.floor(rawData.length / samples);
    const waveformData = [];

    for (let i = 0; i < samples; i++) {
        let sum = 0;
        for (let j = 0; j < blockSize; j++) {
            sum += Math.abs(rawData[i * blockSize + j]);
        }
        waveformData.push(sum / blockSize);
    }

    renderWaveform(waveformData, deck);

    // Estimate BPM
    const bpm = estimateBPM(audioBuffer);
    document.getElementById(`bpm-${deck}`).textContent = `${bpm} BPM`;
}

// Render Waveform to Canvas
function renderWaveform(data, deck) {
    const container = document.getElementById(`waveform-${deck}`);
    container.innerHTML = '';

    const canvas = document.createElement('canvas');
    canvas.width = container.offsetWidth || 300;
    canvas.height = 80;
    container.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    const max = Math.max(...data);
    const barWidth = canvas.width / data.length;
    const color = deck === 'a' ? '#00d4ff' : '#ff6b9d';

    // Draw waveform bars
    data.forEach((val, i) => {
        const height = (val / max) * canvas.height * 0.85;
        const gradient = ctx.createLinearGradient(0, (canvas.height - height) / 2, 0, (canvas.height + height) / 2);
        gradient.addColorStop(0, color);
        gradient.addColorStop(0.5, deck === 'a' ? '#00a3cc' : '#cc5580');
        gradient.addColorStop(1, color);

        ctx.fillStyle = gradient;
        ctx.fillRect(i * barWidth, (canvas.height - height) / 2, barWidth - 1, height);
    });

    // Store canvas for playhead updates
    if (deck === 'a') {
        deckA.canvas = canvas;
        deckA.waveformData = data;
    } else {
        deckB.canvas = canvas;
        deckB.waveformData = data;
    }
}

// Simplified BPM Estimation
function estimateBPM(audioBuffer) {
    const data = audioBuffer.getChannelData(0);
    const sampleRate = audioBuffer.sampleRate;

    // Find peaks in the audio
    let peaks = 0;
    let threshold = 0.7;
    let lastPeak = 0;
    const minPeakDistance = sampleRate * 0.25; // 250ms minimum between peaks

    for (let i = 0; i < data.length; i += 500) {
        if (Math.abs(data[i]) > threshold && i - lastPeak > minPeakDistance) {
            peaks++;
            lastPeak = i;
        }
    }

    const durationSec = audioBuffer.duration;
    let bpm = Math.round((peaks / durationSec) * 60);

    // Clamp to reasonable range and round to common BPM values
    bpm = Math.max(70, Math.min(180, bpm || 120));
    return bpm;
}

// Update Time Display
function updateTimeDisplay(deck) {
    const player = document.getElementById(`deck-${deck}-player`);
    const timeEl = document.querySelector(`#deck-${deck}-info .track-time`);
    const progressEl = document.getElementById(`progress-${deck}`);

    const current = formatTime(player.currentTime);
    const total = formatTime(player.duration || 0);

    timeEl.textContent = `${current} / ${total}`;

    // Update progress bar
    if (player.duration) {
        const progress = (player.currentTime / player.duration) * 100;
        progressEl.style.width = `${progress}%`;
    }

    // Update VU meter (simulated based on volume and playback)
    updateVUMeter(deck, player);
}

function formatTime(seconds) {
    if (isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Toggle Play/Pause
function togglePlay(deck) {
    const player = document.getElementById(`deck-${deck}-player`);
    const btn = document.getElementById(`play-${deck}`);

    if (!player.src) {
        showDJToast(`Load a track on Deck ${deck.toUpperCase()} first`, 'warning');
        return;
    }

    if (player.paused) {
        initAudioContext(); // Ensure audio context is running
        player.play();
        btn.textContent = '⏸';
        btn.classList.add('playing');
    } else {
        player.pause();
        btn.textContent = '▶';
        btn.classList.remove('playing');
    }
}

// Set Volume
function setVolume(deck, value) {
    const player = document.getElementById(`deck-${deck}-player`);
    player.volume = value / 100;
}

// Manual Crossfader
function manualCrossfade(value) {
    const playerA = document.getElementById('deck-a-player');
    const playerB = document.getElementById('deck-b-player');

    // Value 0 = full A, Value 100 = full B
    playerA.volume = (100 - value) / 100;
    playerB.volume = value / 100;
}

// Update Fade Time Display
function updateFadeTime(value) {
    document.getElementById('fade-time').textContent = value;
}

// Set Mix Preset
function setMixPreset(btn, duration) {
    // Update active state
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // Update fade duration slider
    document.getElementById('fade-duration').value = duration;
    document.getElementById('fade-time').textContent = duration;
}

// Enhanced AI Auto Mix with exponential crossfade
function aiAutoMix() {
    const playerA = document.getElementById('deck-a-player');
    const playerB = document.getElementById('deck-b-player');

    if (!deckA || !deckB) {
        showDJToast('Load tracks on both decks first!', 'warning');
        return;
    }

    if (isMixing) {
        showDJToast('Mix already in progress...', 'info');
        return;
    }

    const fadeDuration = parseInt(document.getElementById('fade-duration').value) * 1000;

    // Start deck A if not playing
    if (playerA.paused && !playerB.paused) {
        // If B is playing, mix from B to A
        performMix(playerB, playerA, 'b', 'a', fadeDuration);
    } else if (playerB.paused && !playerA.paused) {
        // If A is playing, mix from A to B
        performMix(playerA, playerB, 'a', 'b', fadeDuration);
    } else if (playerA.paused && playerB.paused) {
        // Neither playing - start A first, then mix to B
        initAudioContext();
        playerA.volume = 1;
        playerB.volume = 0;
        playerA.play();
        document.getElementById('play-a').textContent = '⏸';
        document.getElementById('play-a').classList.add('playing');
        document.getElementById('crossfader').value = 0;

        showDJToast('🎵 Starting Deck A, mix will begin in 3 seconds...', 'info');

        setTimeout(() => {
            performMix(playerA, playerB, 'a', 'b', fadeDuration);
        }, 3000);
    } else {
        // Both playing - mix from A to B
        performMix(playerA, playerB, 'a', 'b', fadeDuration);
    }
}

// Perform the actual mix transition
function performMix(fromPlayer, toPlayer, fromDeck, toDeck, duration) {
    isMixing = true;
    const automixBtn = document.getElementById('automix-btn');
    automixBtn.classList.add('mixing');
    automixBtn.textContent = '🔄 MIXING...';

    showDJToast(`🤖 AI mixing from Deck ${fromDeck.toUpperCase()} to ${toDeck.toUpperCase()}...`, 'info');

    // Start the target deck at 0 volume
    toPlayer.volume = 0;
    if (toPlayer.paused) {
        toPlayer.play();
        document.getElementById(`play-${toDeck}`).textContent = '⏸';
        document.getElementById(`play-${toDeck}`).classList.add('playing');
    }

    const steps = 60; // Smooth animation
    const interval = duration / steps;
    let step = 0;

    const fadeInterval = setInterval(() => {
        step++;
        const progress = step / steps;

        // Exponential curve for natural-sounding crossfade
        const fadeOut = Math.cos(progress * Math.PI / 2);
        const fadeIn = Math.sin(progress * Math.PI / 2);

        fromPlayer.volume = Math.max(0, fadeOut);
        toPlayer.volume = Math.min(1, fadeIn);

        // Update crossfader visual
        const crossfaderValue = fromDeck === 'a' ? progress * 100 : (1 - progress) * 100;
        document.getElementById('crossfader').value = crossfaderValue;

        // Update VU meters
        updateVUMeter(fromDeck, fromPlayer);
        updateVUMeter(toDeck, toPlayer);

        if (step >= steps) {
            clearInterval(fadeInterval);
            fromPlayer.pause();
            document.getElementById(`play-${fromDeck}`).textContent = '▶';
            document.getElementById(`play-${fromDeck}`).classList.remove('playing');

            isMixing = false;
            automixBtn.classList.remove('mixing');
            automixBtn.textContent = '🤖 AI AUTO MIX';

            showDJToast('✨ Mix complete!', 'success');
        }
    }, interval);
}

// Update VU Meter
function updateVUMeter(deck, player) {
    const vuFill = document.querySelector(`#vu-${deck} .vu-fill`);
    if (!vuFill) return;

    // Simulate VU based on volume and whether playing
    let level = 0;
    if (!player.paused) {
        level = player.volume * (70 + Math.random() * 30); // 70-100% when playing
    }
    vuFill.style.height = `${level}%`;
}

// Handle Track End
function handleTrackEnd(deck) {
    const btn = document.getElementById(`play-${deck}`);
    btn.textContent = '▶';
    btn.classList.remove('playing');

    document.getElementById(`progress-${deck}`).style.width = '0%';

    // Auto-play next track if enabled
    if (autoplayEnabled && playlist.length > 0) {
        loadNextFromPlaylist(deck);
    }
}

// Toggle Effects
function toggleEffect(effectType) {
    const btn = document.getElementById(`effect-${effectType}`);
    activeEffects[effectType] = !activeEffects[effectType];

    if (activeEffects[effectType]) {
        btn.classList.add('active');
        showDJToast(`${effectType === 'lowpass' ? 'Low Pass Filter' : 'Echo'} enabled`, 'info');
    } else {
        btn.classList.remove('active');
        showDJToast(`${effectType === 'lowpass' ? 'Low Pass Filter' : 'Echo'} disabled`, 'info');
    }
}

// Playlist Queue Management
function addToQueue(input) {
    const files = input.files;
    if (!files.length) return;

    for (let file of files) {
        const url = URL.createObjectURL(file);
        playlist.push({
            name: file.name.replace(/\.[^/.]+$/, ""),
            file: file,
            url: url
        });
    }

    renderPlaylist();
    showDJToast(`Added ${files.length} track(s) to queue`, 'success');
    input.value = ''; // Reset input
}

function renderPlaylist() {
    const container = document.getElementById('playlist-items');

    if (playlist.length === 0) {
        container.innerHTML = '<div class="playlist-empty">No tracks in queue. Add tracks to enable continuous play!</div>';
        return;
    }

    container.innerHTML = playlist.map((track, index) => `
        <div class="playlist-item" data-index="${index}">
            <span class="track-number">${index + 1}</span>
            <span class="track-title">${escapeHtml(track.name)}</span>
            <button class="remove-btn" onclick="removeFromPlaylist(${index})">✕</button>
        </div>
    `).join('');
}

function removeFromPlaylist(index) {
    playlist.splice(index, 1);
    renderPlaylist();
}

function clearPlaylist() {
    playlist = [];
    renderPlaylist();
    showDJToast('Playlist cleared', 'info');
}

function toggleAutoplay() {
    autoplayEnabled = document.getElementById('autoplay-toggle').checked;
    showDJToast(autoplayEnabled ? 'Auto-play enabled' : 'Auto-play disabled', 'info');
}

function loadNextFromPlaylist(deck) {
    if (playlist.length === 0) return;

    const nextTrack = playlist.shift();
    renderPlaylist();

    // Create a fake file input event
    const player = document.getElementById(`deck-${deck}-player`);
    const nameEl = document.querySelector(`#deck-${deck}-info .track-name`);

    player.src = nextTrack.url;
    player.load();
    nameEl.textContent = nextTrack.name;

    if (deck === 'a') {
        deckA = { file: nextTrack.file, url: nextTrack.url, name: nextTrack.name };
    } else {
        deckB = { file: nextTrack.file, url: nextTrack.url, name: nextTrack.name };
    }

    // Auto-play
    setTimeout(() => {
        player.play();
        document.getElementById(`play-${deck}`).textContent = '⏸';
        document.getElementById(`play-${deck}`).classList.add('playing');
    }, 500);

    showDJToast(`Now playing: ${nextTrack.name}`, 'info');
}

// Toast Notifications
function showDJToast(message, type = 'info') {
    // Remove existing toasts
    document.querySelectorAll('.dj-toast').forEach(t => t.remove());

    const toast = document.createElement('div');
    toast.className = `dj-toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);

    // Auto-hide
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============== WTPT (Where's the Party Tonight) ==============

let wtptEvents = [];
let wtptCurrentCategory = 'all';
let wtptBookings = [];

// Load events when WTPT section is shown
function showSection_original(sectionName) {
    // This function is called from the existing showSection
    if (sectionName === 'wtpt') {
        loadWTPTEvents();
    }
}

// Enhance the existing showSection function
const originalShowSection = window.showSection;
window.showSection = function (sectionName) {
    // Hide all screens
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });

    // Show selected section
    const section = document.getElementById(`${sectionName}-section`);
    if (section) {
        section.classList.add('active');

        // Show the home sub-screen of that section
        const subScreens = section.querySelectorAll('.sub-screen');
        subScreens.forEach(s => s.classList.remove('active'));

        const homeScreen = section.querySelector('.sub-screen');
        if (homeScreen) {
            homeScreen.classList.add('active');
        }

        // Load WTPT events when section is shown
        if (sectionName === 'wtpt') {
            loadWTPTEvents();
        }
    }
};

async function loadWTPTEvents() {
    const city = document.getElementById('wtpt-city').value;
    const grid = document.getElementById('wtpt-events-grid');

    // Show loading
    grid.innerHTML = `
        <div class="loading-events">
            <div class="spinner"></div>
            <p>Finding parties in ${city.charAt(0).toUpperCase() + city.slice(1)}...</p>
        </div>
    `;

    try {
        // Fetch from admin-approved events (no more web scraping)
        const response = await fetch(`/api/wtpt/approved-events?city=${city}`);
        const data = await response.json();

        wtptEvents = data.events || [];

        // Filter by category if needed
        if (wtptCurrentCategory && wtptCurrentCategory !== 'all') {
            wtptEvents = wtptEvents.filter(e => e.category === wtptCurrentCategory);
        }

        renderWTPTEvents();
    } catch (error) {
        console.error('Failed to load events:', error);
        grid.innerHTML = `
            <div class="loading-events">
                <p>😕 No events available right now.</p>
                <p style="color: #888; font-size: 0.9rem; margin-top: 10px;">Events are managed by admin.</p>
            </div>
        `;
    }
}

function getMockEvents() {
    const city = document.getElementById('wtpt-city').value;
    const cityTitled = city.charAt(0).toUpperCase() + city.slice(1);

    // City-specific venues
    const cityVenues = {
        mumbai: {
            club: "Tryst, Lower Parel",
            bar: "Blues Bar, Bandra",
            liveVenue: "Hard Rock Cafe, Worli",
            arena: "Mahalaxmi Racecourse"
        },
        delhi: {
            club: "Kitty Su, The Lalit",
            bar: "Piano Man Jazz Club, Safdarjung",
            liveVenue: "Hard Rock Cafe, Saket",
            arena: "JLN Stadium"
        },
        bangalore: {
            club: "Loft 38, Indiranagar",
            bar: "The Humming Tree, Indiranagar",
            liveVenue: "Hard Rock Cafe, MG Road",
            arena: "Palace Grounds"
        },
        pune: {
            club: "High Spirits, Koregaon Park",
            bar: "Effingut Brewerkz, KP",
            liveVenue: "Hard Rock Cafe, Camp",
            arena: "FC Road"
        },
        goa: {
            club: "Club Cubana, Arpora",
            bar: "Cape Town Cafe, Candolim",
            liveVenue: "LPK Waterfront, Nerul",
            arena: "Vagator Beach"
        },
        hyderabad: {
            club: "Prism Club, Jubilee Hills",
            bar: "Heart Cup Coffee, Kondapur",
            liveVenue: "Hard Rock Cafe, GVK One",
            arena: "Hitex Ground"
        },
        chennai: {
            club: "10 Downing Street, Nungambakkam",
            bar: "The Flying Elephant, Park Hyatt",
            liveVenue: "Dublin, Taramani",
            arena: "YMCA Grounds"
        },
        kolkata: {
            club: "Nocturne, Park Street",
            bar: "Someplace Else, Park Hotel",
            liveVenue: "Hard Rock Cafe, Park Street",
            arena: "Nicco Park"
        }
    };

    const venues = cityVenues[city] || cityVenues.mumbai;

    return [
        {
            id: `mock_001_${city}`,
            title: "Saturday Sundowner - DJ Night",
            category: "dj_night",
            platform: "bookmyshow",
            platform_name: "BookMyShow",
            booking_url: `https://in.bookmyshow.com/explore/music-events-${city === 'delhi' ? 'ncr' : (city === 'bangalore' ? 'bengaluru' : city)}?q=dj+night`,
            venue: venues.club,
            city: cityTitled,
            date: "Dec 28, 2024",
            price: "₹1,500 onwards",
            image: "",
            availability: "Available"
        },
        {
            id: `mock_002_${city}`,
            title: "Karaoke Tuesdays",
            category: "karaoke",
            platform: "district",
            platform_name: "District",
            booking_url: `https://www.district.in/events/?city=${city}&category=music`,
            venue: venues.bar,
            city: cityTitled,
            date: "Every Tuesday",
            price: "₹500 cover",
            image: "",
            availability: "Available"
        },
        {
            id: `mock_003_${city}`,
            title: "Friday Live Music - Acoustic Night",
            category: "live_show",
            platform: "district",
            platform_name: "District",
            booking_url: `https://www.district.in/events/?city=${city}&category=music`,
            venue: venues.liveVenue,
            city: cityTitled,
            date: "Dec 27, 2024",
            price: "₹2,000 onwards",
            image: "",
            availability: "Fast Filling"
        },
        {
            id: `mock_004_${city}`,
            title: "NYE 2025 - Massive Concert",
            category: "concert",
            platform: "bookmyshow",
            platform_name: "BookMyShow",
            booking_url: `https://in.bookmyshow.com/explore/music-events-${city === 'delhi' ? 'ncr' : (city === 'bangalore' ? 'bengaluru' : city)}?q=new+year`,
            venue: venues.arena,
            city: cityTitled,
            date: "Dec 31, 2024",
            price: "₹5,000 onwards",
            image: "",
            availability: "Few Left"
        }
    ];
}

function filterWTPTCategory(category) {
    wtptCurrentCategory = category;

    // Update tab active state
    document.querySelectorAll('.category-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');

    // Reload events with new category
    loadWTPTEvents();
}

function renderWTPTEvents() {
    const grid = document.getElementById('wtpt-events-grid');
    const city = document.getElementById('wtpt-city').value;

    if (!wtptEvents || wtptEvents.length === 0) {
        const categoryName = wtptCurrentCategory === 'all' ? 'events' : wtptCurrentCategory.replace('_', ' ');
        grid.innerHTML = `
            <div class="loading-events">
                <p>🎵 No ${categoryName} found in ${city.charAt(0).toUpperCase() + city.slice(1)}.</p>
                <p style="color: #888; font-size: 0.9rem; margin-top: 10px;">Events are added by admin.</p>
            </div>
        `;
        return;
    }

    const categoryIcons = {
        'dj_night': '🎧',
        'karaoke': '🎤',
        'live_show': '🎸',
        'concert': '🎵',
        'exclusive': '⭐'
    };

    const categoryNames = {
        'dj_night': 'DJ Night',
        'karaoke': 'Karaoke',
        'live_show': 'Live Show',
        'concert': 'Concert',
        'exclusive': 'JukeBob Xclusive'
    };

    // Map admin tags to display
    const tagDisplay = {
        'available': { text: 'Available', class: 'available' },
        'filling_soon': { text: 'Filling Fast', class: 'fast-filling' },
        'sold_out': { text: 'Sold Out', class: 'sold-out' }
    };

    grid.innerHTML = wtptEvents.map((event, idx) => {
        // Map admin fields to legacy display format
        const imageUrl = event.image_url || event.image || '';
        const bookingUrl = event.link || event.booking_url || '#';
        const tag = tagDisplay[event.tag] || { text: 'Available', class: 'available' };
        const dateStr = event.event_datetime
            ? new Date(event.event_datetime).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
            : (event.date || 'TBA');
        const category = event.category || 'concert';
        const icon = categoryIcons[category] || '🎉';

        return `
        <div class="event-card">
            <div class="event-image">
                ${imageUrl ? `<img src="${encodeURI(imageUrl)}" alt="${escapeHtml(event.title)}" onerror="this.style.display='none';">` : icon}
                <span class="platform-badge admin">JukeBob</span>
            </div>
            <div class="event-content">
                <div class="event-header">
                    <span class="event-category">${escapeHtml(categoryNames[category] || 'Event')}</span>
                    <span class="availability-badge ${tag.class}">${escapeHtml(tag.text)}</span>
                </div>
                <h4 class="event-title">${escapeHtml(event.title)}</h4>
                <p class="event-venue">📍 ${escapeHtml(event.venue)}</p>
                <p class="event-date">📅 ${escapeHtml(dateStr)}</p>
                <p class="event-price">💰 ${escapeHtml(event.price)}</p>
                <div class="event-actions">
                    <button class="book-btn ${event.tag === 'sold_out' ? 'sold-out-btn' : ''}"
                            onclick="bookEvent('${encodeURI(bookingUrl)}')"
                            ${event.tag === 'sold_out' ? 'disabled' : ''}>
                        ${event.tag === 'sold_out' ? '🚫 Sold Out' : 'Book Now ↗'}
                    </button>
                    <button class="track-btn" onclick="openBookingModal(${idx})">📝 Track</button>
                </div>
            </div>
        </div>
    `}).join('');
}

function bookEvent(url) {
    if (!/^https?:\/\//i.test(url)) { return; }  // only allow http(s) links
    window.open(url, '_blank', 'noopener');
    showDJToast('Redirecting to booking platform...', 'info');
}

function openBookingModal(index) {
    const event = wtptEvents[index];
    if (!event) return;

    // Populate hidden fields
    document.getElementById('wtpt-event-id').value = event.id;
    document.getElementById('wtpt-event-title').value = event.title;
    document.getElementById('wtpt-event-platform').value = event.platform;
    document.getElementById('wtpt-event-venue').value = event.venue;
    document.getElementById('wtpt-event-date').value = event.date;

    // Show event info
    document.getElementById('booking-event-info').innerHTML = `
        <p><strong>${escapeHtml(event.title)}</strong></p>
        <p>📍 ${escapeHtml(event.venue)}</p>
        <p>📅 ${escapeHtml(event.date || event.event_datetime || '')}</p>
        <p>Platform: ${escapeHtml(event.platform_name || event.platform || 'JukeBob')}</p>
    `;

    document.getElementById('wtpt-booking-modal').style.display = 'flex';
}

function closeWTPTBookingModal() {
    document.getElementById('wtpt-booking-modal').style.display = 'none';
}

async function submitWTPTBooking(event) {
    event.preventDefault();

    const booking = {
        event_id: document.getElementById('wtpt-event-id').value,
        event_title: document.getElementById('wtpt-event-title').value,
        platform: document.getElementById('wtpt-event-platform').value,
        platform_booking_id: document.getElementById('wtpt-booking-id').value,
        user_name: document.getElementById('wtpt-user-name').value,
        user_email: document.getElementById('wtpt-user-email').value,
        user_phone: document.getElementById('wtpt-user-phone').value,
        tickets: parseInt(document.getElementById('wtpt-tickets').value),
        total_amount: parseFloat(document.getElementById('wtpt-amount').value),
        event_date: document.getElementById('wtpt-event-date').value,
        venue: document.getElementById('wtpt-event-venue').value
    };

    try {
        const response = await fetch('/api/wtpt/bookings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(booking)
        });

        const data = await response.json();

        if (data.success) {
            showDJToast('🎉 Booking saved! View in My Bookings.', 'success');
            closeWTPTBookingModal();

            // Switch to bookings view
            showWTPTView('bookings');
            loadWTPTBookings();
        } else {
            showDJToast('Failed to save booking', 'error');
        }
    } catch (error) {
        console.error('Booking error:', error);
        showDJToast('Error saving booking', 'error');
    }
}

function showWTPTView(viewName) {
    // Update tabs
    document.querySelectorAll('.view-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');

    // Show view
    document.querySelectorAll('.wtpt-view').forEach(view => {
        view.classList.remove('active');
    });
    document.getElementById(`wtpt-${viewName}-view`).classList.add('active');

    if (viewName === 'bookings') {
        loadWTPTBookings();
    }
}

async function loadWTPTBookings() {
    const email = localStorage.getItem('wtpt_user_email') || '';

    try {
        const response = await fetch(`/api/wtpt/bookings?email=${email}`);
        const data = await response.json();

        wtptBookings = data.bookings || [];
        renderWTPTBookings();
    } catch (error) {
        console.error('Failed to load bookings:', error);
    }
}

function renderWTPTBookings() {
    const list = document.getElementById('my-bookings-list');

    if (!wtptBookings || wtptBookings.length === 0) {
        list.innerHTML = `
            <div class="no-bookings">
                <p>🎟️ No bookings yet! Find an event and book your tickets.</p>
            </div>
        `;
        return;
    }

    list.innerHTML = wtptBookings.map(booking => `
        <div class="booking-card">
            <div class="booking-info">
                <h4>${escapeHtml(booking.event_title)}</h4>
                <p>📍 ${escapeHtml(booking.venue)} | 📅 ${escapeHtml(booking.event_date)}</p>
                <p>🎫 ${escapeHtml(String(booking.tickets))} ticket(s) | 💰 ₹${Number(booking.total_amount || 0).toLocaleString()}</p>
                <p>Booking ID: ${escapeHtml(booking.id)} | Platform: ${escapeHtml(booking.platform)}</p>
            </div>
            <div class="booking-actions">
                <button class="invoice-btn" onclick="downloadInvoice('${encodeURIComponent(booking.id)}')">📄 Invoice</button>
            </div>
        </div>
    `).join('');
}

function downloadInvoice(bookingId) {
    window.open(`/api/wtpt/invoice/${bookingId}`, '_blank');
    showDJToast('Opening invoice...', 'info');
}

// Handle booking file upload (PDF or image)
async function handleBookingUpload(input) {
    if (input.files.length === 0) return;

    const file = input.files[0];
    showDJToast('Processing your booking...', 'info');

    // For now, we'll open the manual booking modal
    // In future, OCR/AI can parse the file automatically
    try {
        const formData = new FormData();
        formData.append('file', file);

        // Upload the file to extract booking info
        const response = await fetch('/api/tracker/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success && data.tracker) {
            showDJToast('Confirmation uploaded! Please verify details.', 'success');
            // Open booking modal with any extracted info
            openManualBookingModal();
        } else {
            showDJToast('Could not parse file. Please enter manually.', 'warning');
            openManualBookingModal();
        }
    } catch (error) {
        console.error('Upload error:', error);
        showDJToast('Please enter booking details manually.', 'warning');
        openManualBookingModal();
    }

    input.value = ''; // Reset
}

// Open manual booking modal
function openManualBookingModal() {
    // Use the existing WTPT booking modal
    const modal = document.getElementById('wtpt-booking-modal');
    if (modal) {
        // Clear the hidden event fields since this is manual entry
        document.getElementById('wtpt-event-id').value = 'manual_' + Date.now();
        document.getElementById('wtpt-event-title').value = '';
        document.getElementById('wtpt-event-platform').value = 'manual';
        document.getElementById('wtpt-event-venue').value = '';
        document.getElementById('wtpt-event-date').value = '';

        // Update the info display for manual entry
        const infoDiv = document.getElementById('booking-event-info');
        if (infoDiv) {
            infoDiv.innerHTML = `
                <p><strong>Manual Booking Entry</strong></p>
                <p>Enter your booking confirmation details below</p>
            `;
        }

        modal.style.display = 'flex';
    }
}

// ============== TRACK SESSION ==============

let currentTrackers = [];

// Initialize Track Session on page load
function initTrackSession() {
    const uploadZone = document.getElementById('upload-zone');
    if (!uploadZone) return;

    // Drag and drop handlers
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('drag-over');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('drag-over');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            processTrackerFile(files[0]);
        }
    });

    // Load existing trackers
    loadTrackers();
}

// Handle file upload
async function handleTrackerUpload(input) {
    if (input.files.length > 0) {
        await processTrackerFile(input.files[0]);
        input.value = ''; // Reset input
    }
}

// Process uploaded file
async function processTrackerFile(file) {
    const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];

    if (!allowedTypes.includes(file.type) && !file.name.match(/\.(pdf|png|jpg|jpeg|gif|webp)$/i)) {
        showDJToast('Please upload a PDF or image file', 'error');
        return;
    }

    // Show processing indicator
    document.getElementById('tracker-processing').style.display = 'block';

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/tracker/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            showDJToast(`Tracker created: ${data.tracker.name}`, 'success');
            loadTrackers();
        } else {
            showDJToast('Error creating tracker', 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showDJToast('Error uploading file', 'error');
    } finally {
        document.getElementById('tracker-processing').style.display = 'none';
    }
}

// Load all trackers
async function loadTrackers() {
    try {
        const response = await fetch('/api/tracker/list');
        const data = await response.json();

        currentTrackers = data.trackers || [];
        renderTrackers();
    } catch (error) {
        console.error('Error loading trackers:', error);
    }
}

// Render trackers grid
function renderTrackers() {
    const grid = document.getElementById('trackers-grid');

    if (currentTrackers.length === 0) {
        grid.innerHTML = `
            <div class="no-trackers">
                <p>📚 No trackers yet! Upload a PDF or image to get started.</p>
                <button class="btn btn-primary" onclick="createDemoTracker()" style="margin-top: 15px;">
                    🧪 Create Demo Tracker
                </button>
            </div>
        `;
        return;
    }

    grid.innerHTML = currentTrackers.map(tracker => `
        <div class="tracker-item-card" data-tracker-id="${escapeHtml(tracker.id)}">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3>${escapeHtml(tracker.name)}</h3>
                <button onclick="deleteTrackerById('${escapeHtml(tracker.id)}')"
                        style="background: none; border: none; color: #ef4444; cursor: pointer; font-size: 1.2rem;"
                        title="Delete Tracker">🗑️</button>
            </div>
            <div class="tracker-progress">
                <div class="tracker-progress-fill" style="width: ${tracker.progress_percent}%;"></div>
            </div>
            <p style="color: #888; font-size: 0.85rem; margin-bottom: 15px;">
                ${tracker.completed_items}/${tracker.total_items} completed (${tracker.progress_percent}%)
            </p>
            <div class="tracker-items-list">
                ${tracker.items.map(item => `
                    <div class="tracker-check-item ${item.completed ? 'completed' : ''}"
                         onclick="toggleTrackerItem('${escapeHtml(tracker.id)}', '${escapeHtml(item.id)}', ${!item.completed})">
                        <div class="tracker-checkbox"></div>
                        <span class="tracker-item-name">${escapeHtml(item.name)}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `).join('');
}

// Toggle tracker item completion
async function toggleTrackerItem(trackerId, itemId, completed) {
    try {
        const response = await fetch(`/api/tracker/${trackerId}/item`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_id: itemId, completed: completed })
        });

        const data = await response.json();

        if (data.success) {
            // Update local tracker data
            const trackerIndex = currentTrackers.findIndex(t => t.id === trackerId);
            if (trackerIndex >= 0) {
                currentTrackers[trackerIndex] = data.tracker;
            }
            renderTrackers();
        }
    } catch (error) {
        console.error('Error updating item:', error);
        showDJToast('Error updating item', 'error');
    }
}

// Delete a tracker
async function deleteTrackerById(trackerId) {
    if (!confirm('Delete this tracker? This cannot be undone.')) return;

    try {
        const response = await fetch(`/api/tracker/${trackerId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            showDJToast('Tracker deleted', 'info');
            loadTrackers();
        }
    } catch (error) {
        console.error('Error deleting tracker:', error);
        showDJToast('Error deleting tracker', 'error');
    }
}

// Create demo tracker
async function createDemoTracker() {
    try {
        const response = await fetch('/api/tracker/demo', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showDJToast('Demo tracker created!', 'success');
            loadTrackers();
        }
    } catch (error) {
        console.error('Error creating demo:', error);
        showDJToast('Error creating demo tracker', 'error');
    }
}

// Initialize Track Session when tracker section is shown
const _origShowSectionTracker = showSection;
showSection = function (sectionName) {
    _origShowSectionTracker(sectionName);
    if (sectionName === 'tracker') {
        initTrackSession();
    }
};
