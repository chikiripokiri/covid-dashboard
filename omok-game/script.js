const canvas = document.getElementById('omok-board');
const ctx = canvas.getContext('2d');
const turnText = document.getElementById('turn-text');
const turnStone = document.getElementById('turn-stone');
const resetBtn = document.getElementById('reset-btn');
const modal = document.getElementById('modal');
const modalResetBtn = document.getElementById('modal-reset-btn');
const winnerText = document.getElementById('winner-text');

// Game Constants
const BOARD_SIZE = 15;
const GRID_SIZE = 600;
const CELL_SIZE = GRID_SIZE / BOARD_SIZE; // 40px
const PADDING = CELL_SIZE / 2; // Center the grid intersections

// Game State
let board = []; // 0: Empty, 1: Black, 2: White
let currentPlayer = 1; // 1: Black, 2: White
let gameActive = true;

// Init
function init() {
    initBoardState();
    drawBoard();

    // Event Listeners
    canvas.addEventListener('click', handleClick);
    // Add mousemove for hover effect? (Optional optimization)
    // canvas.addEventListener('mousemove', handleHover);

    resetBtn.addEventListener('click', resetGame);
    modalResetBtn.addEventListener('click', resetGame);
}

function initBoardState() {
    board = Array(BOARD_SIZE).fill().map(() => Array(BOARD_SIZE).fill(0));
    currentPlayer = 1;
    gameActive = true;
    updateTurnUI();
}

function drawBoard() {
    // Clear
    ctx.clearRect(0, 0, GRID_SIZE, GRID_SIZE);

    // Draw Grid Lines
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    ctx.beginPath();

    for (let i = 0; i < BOARD_SIZE; i++) {
        // Horizontal
        ctx.moveTo(PADDING, PADDING + i * CELL_SIZE);
        ctx.lineTo(GRID_SIZE - PADDING, PADDING + i * CELL_SIZE);

        // Vertical
        ctx.moveTo(PADDING + i * CELL_SIZE, PADDING);
        ctx.lineTo(PADDING + i * CELL_SIZE, GRID_SIZE - PADDING);
    }
    ctx.stroke();

    // Draw Star Points (Tengen and Hoshi)
    const stars = [3, 7, 11];
    ctx.fillStyle = '#111';
    stars.forEach(r => {
        stars.forEach(c => {
            ctx.beginPath();
            ctx.arc(PADDING + c * CELL_SIZE, PADDING + r * CELL_SIZE, 4, 0, Math.PI * 2);
            ctx.fill();
        });
    });

    // Draw Stones
    for (let r = 0; r < BOARD_SIZE; r++) {
        for (let c = 0; c < BOARD_SIZE; c++) {
            if (board[r][c] !== 0) {
                drawStone(r, c, board[r][c]);
            }
        }
    }
}

function drawStone(r, c, player) {
    const x = PADDING + c * CELL_SIZE;
    const y = PADDING + r * CELL_SIZE;
    const radius = CELL_SIZE * 0.45;

    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);

    // Stone Gradient
    const gradient = ctx.createRadialGradient(
        x - radius / 3, y - radius / 3, radius / 10,
        x, y, radius
    );

    if (player === 1) { // Black
        gradient.addColorStop(0, '#555');
        gradient.addColorStop(1, '#000');
        // Shadow
        ctx.shadowColor = 'rgba(0,0,0,0.5)';
        ctx.shadowBlur = 5;
        ctx.shadowOffsetX = 2;
        ctx.shadowOffsetY = 2;
    } else { // White
        gradient.addColorStop(0, '#fff');
        gradient.addColorStop(1, '#ddd');
        // Shadow
        ctx.shadowColor = 'rgba(0,0,0,0.4)';
        ctx.shadowBlur = 5;
        ctx.shadowOffsetX = 2;
        ctx.shadowOffsetY = 2;
    }

    ctx.fillStyle = gradient;
    ctx.fill();

    // Reset shadow for performance
    ctx.shadowColor = 'transparent';
}

function handleClick(e) {
    if (!gameActive) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Convert click to index
    // To ensure "snap" to intersection, we round to nearest index
    // x = PADDING + c * CELL_SIZE  => c = (x - PADDING) / CELL_SIZE
    const c = Math.round((x - PADDING) / CELL_SIZE);
    const r = Math.round((y - PADDING) / CELL_SIZE);

    // Bounds check
    if (r < 0 || r >= BOARD_SIZE || c < 0 || c >= BOARD_SIZE) return;

    // Occupied check
    if (board[r][c] !== 0) return;

    placeStone(r, c);
}

function placeStone(r, c) {
    board[r][c] = currentPlayer;
    drawBoard(); // Redraw with new stone on top

    // Check Win
    if (checkWin(r, c, currentPlayer)) {
        endGame(currentPlayer);
        return;
    }

    // Toggle Turn
    currentPlayer = currentPlayer === 1 ? 2 : 1;
    updateTurnUI();
}

function checkWin(r, c, player) {
    const directions = [
        [0, 1],  // Horizontal
        [1, 0],  // Vertical
        [1, 1],  // Diagonal (Top-Left to Bottom-Right)
        [1, -1]  // Anti-Diagonal (Top-Right to Bottom-Left)
    ];

    for (let [dr, dc] of directions) {
        let count = 1;

        // Check forward
        for (let i = 1; i < 5; i++) {
            const nr = r + dr * i;
            const nc = c + dc * i;
            if (isValid(nr, nc) && board[nr][nc] === player) count++;
            else break;
        }

        // Check backward
        for (let i = 1; i < 5; i++) {
            const nr = r - dr * i;
            const nc = c - dc * i;
            if (isValid(nr, nc) && board[nr][nc] === player) count++;
            else break;
        }

        if (count >= 5) return true;
    }
    return false;
}

function isValid(r, c) {
    return r >= 0 && r < BOARD_SIZE && c >= 0 && c < BOARD_SIZE;
}

function endGame(winner) {
    gameActive = false;
    winnerText.innerText = winner === 1 ? "흑돌(Black) 승리!" : "백돌(White) 승리!";
    modal.classList.remove('hidden');
}

function resetGame() {
    modal.classList.add('hidden');
    initBoardState();
    drawBoard();
}

function updateTurnUI() {
    if (currentPlayer === 1) {
        turnText.innerText = "흑돌(Black) 차례";
        turnStone.classList.remove('white');
        turnStone.classList.add('black');
    } else {
        turnText.innerText = "백돌(White) 차례";
        turnStone.classList.remove('black');
        turnStone.classList.add('white');
    }
}

// Start
init();
