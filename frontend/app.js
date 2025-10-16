// Global state
let currentSession = null;
let currentUser = null;
let ws = null;
let currentGame = null;
let deckA = null;
let deckB = null;

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
    switch(data.type) {
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
                renderTicTacToe();
            }
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
        await fetch(`/api/requests/${requestId}/complete?session_id=${currentSession}`, {
            method: 'POST'
        });
        refreshJukebox();
    } catch (error) {
        alert('Error completing request: ' + error.message);
    }
}

async function skipRequest(requestId) {
    try {
        await fetch(`/api/requests/${requestId}/skip?session_id=${currentSession}`, {
            method: 'POST'
        });
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
        
        const totalTips = requests.reduce((sum, r) => sum + r.tip_amount, 0);
        
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
    
    requests.forEach((req, index) => {
        const card = document.createElement('div');
        card.className = 'request-card';
        card.innerHTML = `
            <div class="request-info">
                <h4>#${index + 1} ${req.song_name}</h4>
                <p>${req.artist} • ${req.requester_name}</p>
                <p>💰 Tip: ₹${req.tip_amount.toFixed(2)}</p>
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
                <h4>${req.song_name}</h4>
                <p>${req.artist} • ${req.requester_name}</p>
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
                session_id: currentSession.session_id,
                payment_method: method,
                upi_id: method === 'upi' ? 'artist@upi' : null
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
            yourSymbol: 'X'
        };
        
        // Connect WebSocket for real-time updates
        connectGameWebSocket(data.room_code);
        
        document.getElementById('ttt-room-code').textContent = data.room_code;
        renderTicTacToe();
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
            yourSymbol: 'O'
        };
        
        // Connect WebSocket for real-time updates
        connectGameWebSocket(gameCode);
        
        document.getElementById('ttt-room-code').textContent = gameCode;
        renderTicTacToe();
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
        const yourSymbol = room.player1 === localStorage.getItem('playerName') ? 'X' : 'O';
        
        currentGame = {
            code: gameCode,
            type: room.type,
            player1: room.player1,
            player2: room.player2,
            board: room.board,
            currentTurn: room.current_turn,
            yourSymbol: yourSymbol
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
    
    try {
        const response = await fetch('/api/games/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                room_code: currentGame.code,
                player_name: currentUser?.name || localStorage.getItem('playerName'),
                move: index
            })
        });
        
        if (!response.ok) throw new Error('Invalid move');
        
        const data = await response.json();
        currentGame.board = data.room.board;
        currentGame.currentTurn = data.room.current_turn;
        
        renderTicTacToe();
        
        const winner = checkWinner();
        if (winner) {
            document.getElementById('ttt-result').textContent = 
                winner === currentGame.yourSymbol ? 'You Won! 🎉' : 'You Lost!';
        } else if (currentGame.board.every(cell => cell)) {
            document.getElementById('ttt-result').textContent = "It's a Draw!";
        }
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

// ============== AI DJ ==============

function loadTrack(deck, input) {
    const file = input.files[0];
    if (!file) return;
    
    const url = URL.createObjectURL(file);
    const player = document.getElementById(`deck-${deck}-player`);
    const info = document.getElementById(`deck-${deck}-info`);
    
    // Ensure the audio element loads the file properly
    player.src = url;
    player.load(); // Force load the audio file
    
    info.innerHTML = `
        <p><strong>${file.name}</strong></p>
        <p>Size: ${(file.size / 1024 / 1024).toFixed(2)} MB</p>
        <p>Type: ${file.type}</p>
    `;
    
    // Store deck information
    if (deck === 'a') {
        deckA = { file, url };
    } else {
        deckB = { file, url };
    }
    
    // Add event listener to handle playback
    player.addEventListener('canplaythrough', () => {
        info.innerHTML += '<p style="color: #00d4ff;">✓ Ready to play</p>';
    });
    
    player.addEventListener('error', (e) => {
        info.innerHTML += '<p style="color: #ff6b6b;">✗ Error loading file</p>';
        console.error('Audio loading error:', e);
    });
}

function aiAutoMix() {
    const playerA = document.getElementById('deck-a-player');
    const playerB = document.getElementById('deck-b-player');
    
    if (!deckA || !deckB) {
        alert('Please load both tracks first!');
        return;
    }
    
    // Simple auto-mix simulation
    playerA.play();
    
    setTimeout(() => {
        playerB.play();
        
        // Crossfade simulation
        let fadeValue = 0;
        const fadeInterval = setInterval(() => {
            fadeValue += 2;
            document.getElementById('crossfader').value = fadeValue;
            
            playerA.volume = (100 - fadeValue) / 100;
            playerB.volume = fadeValue / 100;
            
            if (fadeValue >= 100) {
                clearInterval(fadeInterval);
                playerA.pause();
            }
        }, 100);
    }, 3000);
    
    alert('🤖 AI Auto-mix started! Watch the magic happen...');
}
