// State
let currentRound = 0;
const MAX_ROUNDS = 10;
let reactionTimes = [];
let startTime = 0;
let timerId = null;
let gameActive = false; // Prevent clicks before game starts or during delays

// DOM Elements
const startScreen = document.getElementById('start-screen');
const gameScreen = document.getElementById('game-screen');
const resultScreen = document.getElementById('result-screen');
const gameOverScreen = document.getElementById('game-over-screen');

const startBtn = document.getElementById('start-btn');
const retryBtnFail = document.getElementById('retry-btn-fail');
const retryBtnSuccess = document.getElementById('retry-btn-success');
const targetBtn = document.getElementById('target-btn');
const gameArea = document.getElementById('game-area');
const roundCounter = document.getElementById('round-counter');

// Results
const finalScoreEl = document.getElementById('final-score');
const avgScoreEl = document.getElementById('average-score');
const leaderboardStart = document.getElementById('leaderboard-list-start');
const leaderboardResult = document.getElementById('leaderboard-list-result');

// Input
const saveScoreBtn = document.getElementById('save-score-btn');
const playerNameInput = document.getElementById('player-name');
const saveScoreSection = document.getElementById('save-score-section');

// Init
function init() {
    renderLeaderboard();

    startBtn.addEventListener('click', startGame);
    retryBtnFail.addEventListener('click', () => resetGame());
    retryBtnSuccess.addEventListener('click', () => resetGame());
    saveScoreBtn.addEventListener('click', () => handleSaveScore());

    // Global click listener for game area
    gameArea.addEventListener('mousedown', handleInput);
}

function resetGame() {
    showScreen(startScreen);
    renderLeaderboard(); // Update in case it changed
}

function startGame() {
    currentRound = 0;
    reactionTimes = [];
    showScreen(gameScreen);
    updateHUD();
    nextRound();
}

function nextRound() {
    if (currentRound >= MAX_ROUNDS) {
        finishGame();
        return;
    }

    currentRound++;
    updateHUD();
    gameActive = false; // Waiting for target to appear
    targetBtn.style.display = 'none';

    // Random delay between 500ms and 3000ms
    const delay = Math.floor(Math.random() * 2500) + 500;

    timerId = setTimeout(() => {
        showTarget();
    }, delay);
}

function showTarget() {
    gameActive = true; // Target is now visible, clicks on target are valid

    // Get viewport dimensions
    // Safe margin from edges (e.g., 100px)
    const padding = 100;
    const btnSize = 80; // Defined in CSS

    // Available area calculation
    const maxX = window.innerWidth - btnSize - padding;
    const maxY = window.innerHeight - btnSize - padding;

    const randomX = Math.floor(Math.random() * (maxX - padding)) + padding;
    const randomY = Math.floor(Math.random() * (maxY - padding)) + padding;

    targetBtn.style.left = `${randomX}px`;
    targetBtn.style.top = `${randomY}px`;
    targetBtn.style.display = 'block';

    startTime = Date.now();
}

function handleInput(e) {
    // If we are not in the 'active' phase of a round (e.g. waiting for button), ignore or punish?
    // Rule: "button appears ... click it"
    // If waiting for button (gameActive = false) and user clicks -> strictly speaking, False Start.
    // For now, let's only punish spills *after* button appears or if they click background while button is there.

    // Design decision: If the screen is Game Screen, any click on background is Game Over.
    // We need to differentiate 'waiting period' clicks vs 'missed button' clicks.
    // Simpler rule: Any click on #game-area that is NOT the target is a MISS (Game Over).
    // EXCEPT if we are waiting for the button to appear? Usually reaction tests punish early clicks too.
    // Let's implement strict: Click anywhere not target = Game Over.

    if (e.target.id === 'target-btn') {
        if (!gameActive) return; // Should not happen if display is none

        const endTime = Date.now();
        const reactionTime = endTime - startTime;
        reactionTimes.push(reactionTime);

        targetBtn.style.display = 'none';
        gameActive = false;

        // Prevent double clicks processing
        e.stopPropagation();

        nextRound();
    } else {
        // Background click
        gameOver();
    }
}

function gameOver() {
    clearTimeout(timerId);
    gameActive = false;
    showScreen(gameOverScreen);
}

function finishGame() {
    const totalTime = reactionTimes.reduce((a, b) => a + b, 0);
    const avgTime = Math.floor(totalTime / MAX_ROUNDS);

    finalScoreEl.innerText = `${totalTime}ms`;
    avgScoreEl.innerText = `${avgTime}ms`;

    // Show input section
    saveScoreSection.style.display = 'flex';
    playerNameInput.value = '';

    // If we want to show current ranking context, we can render existing leaderboard first
    renderLeaderboard();
    showScreen(resultScreen);
}

// Leaderboard / LocalStorage
function handleSaveScore() {
    const name = playerNameInput.value.trim() || 'ANONYMOUS';
    const totalTime = reactionTimes.reduce((a, b) => a + b, 0);

    saveScore(name, totalTime);

    // Hide input after saving
    saveScoreSection.style.display = 'none';
    renderLeaderboard();
}

function saveScore(name, score) {
    const history = JSON.parse(localStorage.getItem('reactionLeaderboard') || '[]');
    const newEntry = {
        name: name,
        score: score,
        date: new Date().toLocaleDateString()
    };

    history.push(newEntry);
    history.sort((a, b) => a.score - b.score);

    // Keep top 5
    if (history.length > 5) {
        history.length = 5;
    }

    localStorage.setItem('reactionLeaderboard', JSON.stringify(history));
}

function renderLeaderboard() {
    const history = JSON.parse(localStorage.getItem('reactionLeaderboard') || '[]');

    const createList = (list) => {
        if (history.length === 0) {
            return '<li><span class="date">No records yet.</span></li>';
        }
        return history.map((item, index) => `
            <li>
                <div>
                    <span class="rank">#${index + 1}</span>
                    <span class="name" style="color: #fff; font-weight:600; margin-right:1rem;">${item.name || 'ANON'}</span>
                    <span class="timeout">${item.score}ms</span>
                </div>
                <span class="date">${item.date}</span>
            </li>
        `).join('');
    };

    const html = createList();
    if (leaderboardStart) leaderboardStart.innerHTML = html;
    if (leaderboardResult) leaderboardResult.innerHTML = html;
}


// Utils
function showScreen(screen) {
    // Hide all
    [startScreen, gameScreen, resultScreen, gameOverScreen].forEach(s => s.classList.remove('active'));
    // Show one
    if (screen) screen.classList.add('active');
}

function updateHUD() {
    roundCounter.innerText = currentRound;
}

// Run
init();
