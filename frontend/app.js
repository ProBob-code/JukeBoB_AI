let currentSession = null;
let currentUser = null;
let ws = null;

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(screenId).classList.add('active');
}

async function createSession(event) {
    event.preventDefault();
    
    const partyName = document.getElementById('party-name').value;
    const artistName = document.getElementById('artist-name').value;
    
    try {
        const response = await fetch('/api/sessions/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: partyName,
                artist_id: artistName
            })
        });
        
        const data = await response.json();
        currentSession = data.session_id;
        currentUser = { name: artistName, role: 'artist' };
        
        document.getElementById('artist-party-name').textContent = partyName;
        document.getElementById('session-code-display').textContent = data.session_id;
        document.getElementById('qr-code').src = 'data:image/png;base64,' + data.qr_code;
        
        connectWebSocket(data.session_id);
        showScreen('artist-screen');
        loadArtistRequests();
    } catch (error) {
        alert('Error creating session: ' + error.message);
    }
}

async function joinSession(event) {
    event.preventDefault();
    
    const sessionCode = document.getElementById('session-code').value.toUpperCase();
    const guestName = document.getElementById('guest-name').value;
    
    try {
        const response = await fetch(`/api/sessions/${sessionCode}`);
        if (!response.ok) throw new Error('Session not found');
        
        const session = await response.json();
        currentSession = sessionCode;
        currentUser = { name: guestName, role: 'guest' };
        
        document.getElementById('party-name-display').textContent = session.name;
        
        connectWebSocket(sessionCode);
        showScreen('party-screen');
        loadPartyRequests();
    } catch (error) {
        alert('Error joining session: ' + error.message);
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
            addRequestToUI(data.request);
            break;
        case 'voting_started':
            showVotingBanner(data.duration);
            break;
        case 'vote_update':
            updateVoteCount(data.request_id, data.votes);
            break;
        case 'voting_ended':
            hideVotingBanner();
            refreshRequests();
            break;
        case 'tip_added':
            updateTipAmount(data.request_id, data.total_tips);
            break;
        case 'request_completed':
        case 'request_skipped':
            refreshRequests();
            break;
    }
}

async function submitRequest(event) {
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
        
        const data = await response.json();
        closeRequestForm();
        event.target.reset();
    } catch (error) {
        alert('Error submitting request: ' + error.message);
    }
}

async function voteForRequest(requestId) {
    try {
        await fetch('/api/requests/vote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSession,
                request_id: requestId
            })
        });
    } catch (error) {
        alert('Error voting: ' + error.message);
    }
}

async function completeRequest(requestId) {
    try {
        await fetch(`/api/requests/${requestId}/complete?session_id=${currentSession}`, {
            method: 'POST'
        });
    } catch (error) {
        alert('Error completing request: ' + error.message);
    }
}

async function skipRequest(requestId) {
    try {
        await fetch(`/api/requests/${requestId}/skip?session_id=${currentSession}`, {
            method: 'POST'
        });
    } catch (error) {
        alert('Error skipping request: ' + error.message);
    }
}

async function loadPartyRequests() {
    try {
        const response = await fetch(`/api/requests/${currentSession}`);
        const requests = await response.json();
        
        const container = document.getElementById('party-requests');
        container.innerHTML = '';
        
        const pendingRequests = requests.filter(r => r.status === 'pending');
        const queuedRequests = requests.filter(r => r.status === 'queued');
        
        [...queuedRequests, ...pendingRequests].forEach(request => {
            addRequestToUI(request);
        });
    } catch (error) {
        console.error('Error loading requests:', error);
    }
}

async function loadArtistRequests() {
    try {
        const response = await fetch(`/api/requests/${currentSession}`);
        const requests = await response.json();
        
        const container = document.getElementById('artist-queue');
        container.innerHTML = '';
        
        const totalRequests = requests.length;
        const totalTips = requests.reduce((sum, r) => sum + r.tip_amount, 0);
        
        document.getElementById('total-requests').textContent = totalRequests;
        document.getElementById('total-tips').textContent = '$' + totalTips.toFixed(2);
        
        const activeRequests = requests.filter(r => 
            r.status === 'pending' || r.status === 'queued'
        );
        
        activeRequests.forEach(request => {
            const card = createArtistRequestCard(request);
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading requests:', error);
    }
}

function addRequestToUI(request) {
    const container = currentUser.role === 'artist' 
        ? document.getElementById('artist-queue')
        : document.getElementById('party-requests');
    
    const card = currentUser.role === 'artist' 
        ? createArtistRequestCard(request)
        : createGuestRequestCard(request);
    
    container.insertBefore(card, container.firstChild);
}

function createGuestRequestCard(request) {
    const card = document.createElement('div');
    card.className = `request-card status-${request.status}`;
    card.id = `request-${request.id}`;
    
    card.innerHTML = `
        <div class="request-info">
            <h4>${request.song_name}</h4>
            <p>${request.artist} • Requested by ${request.requester_name}</p>
            ${request.tip_amount > 0 ? `<p>💰 Tip: $${request.tip_amount.toFixed(2)}</p>` : ''}
        </div>
        <div class="request-actions">
            ${request.status === 'pending' ? `
                <span class="votes" id="votes-${request.id}">${request.votes} votes</span>
                <button class="vote-btn" onclick="voteForRequest('${request.id}')">Vote</button>
            ` : ''}
            ${request.status === 'queued' ? '<span class="votes">✅ Queued</span>' : ''}
        </div>
    `;
    
    return card;
}

function createArtistRequestCard(request) {
    const card = document.createElement('div');
    card.className = `request-card status-${request.status}`;
    card.id = `request-${request.id}`;
    
    card.innerHTML = `
        <div class="request-info">
            <h4>${request.song_name}</h4>
            <p>${request.artist} • Requested by ${request.requester_name}</p>
            ${request.tip_amount > 0 ? `<p>💰 Tip: $${request.tip_amount.toFixed(2)}</p>` : ''}
        </div>
        <div class="request-actions">
            ${request.status === 'pending' ? `<span class="votes" id="votes-${request.id}">${request.votes} votes</span>` : ''}
            ${request.status === 'queued' ? `
                <button class="complete-btn" onclick="completeRequest('${request.id}')">✓ Played</button>
                <button class="skip-btn" onclick="skipRequest('${request.id}')">✗ Skip</button>
            ` : ''}
        </div>
    `;
    
    return card;
}

function updateVoteCount(requestId, votes) {
    const voteElement = document.getElementById(`votes-${requestId}`);
    if (voteElement) {
        voteElement.textContent = `${votes} votes`;
    }
}

function updateTipAmount(requestId, totalTips) {
    const card = document.getElementById(`request-${requestId}`);
    if (card) {
        loadArtistRequests();
    }
}

function showVotingBanner(duration) {
    const banner = document.getElementById('voting-banner');
    banner.style.display = 'block';
    
    let timeLeft = duration;
    const timer = setInterval(() => {
        timeLeft--;
        document.getElementById('voting-timer').textContent = `${timeLeft}s`;
        
        if (timeLeft <= 0) {
            clearInterval(timer);
        }
    }, 1000);
}

function hideVotingBanner() {
    document.getElementById('voting-banner').style.display = 'none';
}

function showRequestForm() {
    document.getElementById('request-modal').classList.add('active');
}

function closeRequestForm() {
    document.getElementById('request-modal').classList.remove('active');
}

function refreshRequests() {
    if (currentUser.role === 'artist') {
        loadArtistRequests();
    } else {
        loadPartyRequests();
    }
}

function endSession() {
    if (confirm('Are you sure you want to end this session?')) {
        if (ws) ws.close();
        currentSession = null;
        currentUser = null;
        showScreen('home-screen');
    }
}

function leaveParty() {
    if (ws) ws.close();
    currentSession = null;
    currentUser = null;
    showScreen('home-screen');
}
