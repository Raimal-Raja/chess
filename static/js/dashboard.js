let currentGameId = null;
let selectedSquare = null;
let validMoves = [];
let isGameActive = false;
let currentPlayer = 'white';
let gameType = null;
let moveHistory = [];
let capturedPieces = { white: [], black: [] };
let gameStartTime = null;
let timerInterval = null;
let moveAnalysis = {
    white: { excellent: 0, good: 0, inaccuracies: 0, mistakes: 0, blunders: 0 },
    black: { excellent: 0, good: 0, inaccuracies: 0, mistakes: 0, blunders: 0 }
};
let previousBoardState = null;
let boardHistory = [];
let socket = null;

// Chess pieces Unicode
const pieces = {
    'white': {
        'rook': '♖', 'knight': '♘', 'bishop': '♗', 
        'queen': '♕', 'king': '♔', 'pawn': '♙'
    },
    'black': {
        'rook': '♜', 'knight': '♞', 'bishop': '♝', 
        'queen': '♛', 'king': '♚', 'pawn': '♟'
    }
};


// Sound effect URLs
const soundEffects = {
    move: 'https://cdn.jsdelivr.net/gh/lichess-org/lila@master/public/sound/standard/Move.mp3',
    capture: 'https://cdn.jsdelivr.net/gh/lichess-org/lila@master/public/sound/standard/Capture.mp3',
    check: 'https://cdn.jsdelivr.net/gh/lichess-org/lila@master/public/sound/standard/GenericNotify.mp3',
    checkmate: 'https://cdn.jsdelivr.net/gh/lichess-org/lila@master/public/sound/standard/Victory.mp3',
    castle: 'https://cdn.jsdelivr.net/gh/lichess-org/lila@master/public/sound/standard/Castle.mp3'
};

const audioCache = {};

function preloadSounds() {
    Object.keys(soundEffects).forEach(key => {
        audioCache[key] = new Audio(soundEffects[key]);
        audioCache[key].preload = 'auto';
        audioCache[key].volume = 0.5;
    });
    console.log('Chess sounds preloaded successfully');
}

function playSound(soundType) {
    try {
        if (audioCache[soundType]) {
            // Clone the audio to allow overlapping sounds
            const sound = audioCache[soundType].cloneNode();
            sound.volume = 0.5;
            sound.play().catch(err => {
                console.log('Sound play failed:', err);
            });
        }
    } catch (error) {
        console.log('Error playing sound:', error);
    }
}

function checkForCheck(boardData, color) {
    // This function checks if the specified color's king is in check
    // You'll need to implement the logic based on your board state
    fetch('/api/is_in_check', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            game_id: currentGameId,
            color: color
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.in_check) {
            playSound('check');
            const message = `${color.charAt(0).toUpperCase() + color.slice(1)} King is in Check!`;
            const statusDiv = document.getElementById('statusMessage');
            if (statusDiv) {
                statusDiv.textContent = message;
                statusDiv.style.color = '#ff4444';
                statusDiv.style.fontWeight = 'bold';
                
                // Flash the board border to indicate check
                const board = document.getElementById('chessboard');
                if (board) {
                    board.style.boxShadow = '0 0 20px 5px rgba(255, 68, 68, 0.8)';
                    setTimeout(() => {
                        board.style.boxShadow = '';
                    }, 2000);
                }
                
                setTimeout(() => {
                    statusDiv.style.color = '';
                    statusDiv.style.fontWeight = '';
                }, 2000);
            }
        }
    })
    .catch(error => console.error('Error checking for check:', error));
}

function updateVolume(value) {
    const volume = value / 100;
    Object.keys(audioCache).forEach(key => {
        audioCache[key].volume = volume;
    });
    const volumeDisplay = document.getElementById('volumeValue');
    if (volumeDisplay) {
        volumeDisplay.textContent = value + '%';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeBoard();
    updateMoveAnalysisDisplay();
    initializeSocketIO();
    preloadSounds(); // Preload all chess sounds
    
    // Add volume control if it doesn't exist
    const volumeControl = document.getElementById('volumeControl');
    if (volumeControl) {
        volumeControl.addEventListener('input', function(e) {
            updateVolume(e.target.value);
        });
    }
});



// Initialize SocketIO connection
function initializeSocketIO() {
    if (typeof io !== 'undefined') {
        socket = io();
        
        // Listen for bot moves
        socket.on('bot_moved', function(data) {
            console.log('Bot moved:', data);
            handleBotMove(data);
        });
        
        socket.on('game_state', function(data) {
            console.log('Game state update:', data);
        });
        
        socket.on('error', function(data) {
            console.error('Socket error:', data);
            alert(data.message || 'Connection error');
        });
        
        console.log('SocketIO initialized');
    } else {
        console.warn('SocketIO not available');
    }
}

// Handle bot move from server
function handleBotMove(data) {
    if (!isGameActive) return;
    
    console.log('Processing bot move');
    
    selectedSquare = null;
    validMoves = [];
    
    // Determine which sound to play for bot move
    const wasCaptured = data.bot_move && data.captured_pieces && 
                       (data.captured_pieces.white.length + data.captured_pieces.black.length > 
                        capturedPieces.white.length + capturedPieces.black.length);
    
    if (wasCaptured) {
        playSound('capture'); // Bot captured a piece
    } else {
        playSound('move'); // Regular bot move
    }
    
    updateBoard(data.board, data.bot_move);
    currentPlayer = data.next_player;
    updateTurnIndicator();
    
    if (data.captured_pieces) {
        capturedPieces = data.captured_pieces;
        updateCapturedPieces();
    }
    
    if (data.bot_move) {
        addMoveToHistory(data.bot_move);
        analyzeMoveQuality('black');
    }
    
    // Check if bot put player in check
    if (!data.game_over) {
        checkForCheck(data.board, currentPlayer);
    }
    
    if (data.game_over) {
        // Play checkmate sound if bot checkmated the player
        if (data.result === 'checkmate') {
            playSound('checkmate');
        }
        handleGameOver(data);
    } else {
        updateGameStatus("Your turn");
    }
}

// Sidebar Toggle
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    
    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');
}

// Initialize empty chess board
function initializeBoard() {
    const board = document.getElementById('chessboard');
    board.innerHTML = '';
    
    const initialBoard = [
        ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook'],
        ['pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn'],
        Array(8).fill(null),
        Array(8).fill(null),
        Array(8).fill(null),
        Array(8).fill(null),
        ['pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn'],
        ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook']
    ];

    for (let row = 0; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
            const square = document.createElement('div');
            square.className = `square ${(row + col) % 2 === 0 ? 'light' : 'dark'}`;
            square.dataset.row = row;
            square.dataset.col = col;
            
            if (col === 0) {
                const rowLabel = document.createElement('span');
                rowLabel.className = 'row-label';
                rowLabel.textContent = 8 - row;
                square.appendChild(rowLabel);
            }
            if (row === 7) {
                const colLabel = document.createElement('span');
                colLabel.className = 'col-label';
                colLabel.textContent = String.fromCharCode(97 + col);
                square.appendChild(colLabel);
            }
            
            if (initialBoard[row][col]) {
                const piece = document.createElement('span');
                piece.className = 'piece';
                const color = row < 2 ? 'black' : 'white';
                piece.textContent = pieces[color][initialBoard[row][col]];
                piece.dataset.color = color;
                piece.dataset.type = initialBoard[row][col];
                square.appendChild(piece);
            }
            
            square.addEventListener('click', () => handleSquareClick(row, col));
            board.appendChild(square);
        }
    }
}

// Update board with game state
function updateBoard(boardData, lastMove = null) {
    const board = document.getElementById('chessboard');
    board.innerHTML = '';

    for (let row = 0; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
            const square = document.createElement('div');
            square.className = `square ${(row + col) % 2 === 0 ? 'light' : 'dark'}`;
            square.dataset.row = row;
            square.dataset.col = col;
            
            if (col === 0) {
                const rowLabel = document.createElement('span');
                rowLabel.className = 'row-label';
                rowLabel.textContent = 8 - row;
                square.appendChild(rowLabel);
            }
            if (row === 7) {
                const colLabel = document.createElement('span');
                colLabel.className = 'col-label';
                colLabel.textContent = String.fromCharCode(97 + col);
                square.appendChild(colLabel);
            }
            
            if (lastMove && 
                ((lastMove.initial.row === row && lastMove.initial.col === col) ||
                 (lastMove.final.row === row && lastMove.final.col === col))) {
                square.classList.add('last-move');
            }
            
            if (boardData[row][col]) {
                const pieceData = boardData[row][col];
                const piece = document.createElement('span');
                piece.className = 'piece';
                piece.textContent = pieces[pieceData.color][pieceData.name];
                piece.dataset.color = pieceData.color;
                piece.dataset.type = pieceData.name;
                square.appendChild(piece);
            }
            
            if (selectedSquare && selectedSquare.row === row && selectedSquare.col === col) {
                square.classList.add('selected');
            }
            
            if (validMoves.some(move => move.row === row && move.col === col)) {
                square.classList.add('valid-move');
                const dot = document.createElement('span');
                dot.className = 'move-dot';
                square.appendChild(dot);
            }
            
            square.addEventListener('click', () => handleSquareClick(row, col));
            board.appendChild(square);
        }
    }
}

// Handle square click
function handleSquareClick(row, col) {
    if (!isGameActive || !currentGameId) {
        return;
    }

    // Prevent moves during bot's turn
    if (gameType === 'bot' && currentPlayer === 'black') {
        return;
    }

    if (selectedSquare && validMoves.some(move => move.row === row && move.col === col)) {
        makeMove(row, col);
    } else {
        selectSquare(row, col);
    }
}

// Select a square
function selectSquare(row, col) {
    fetch('/api/select_square', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            game_id: currentGameId,
            row: row,
            col: col
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.valid_moves && data.valid_moves.length > 0) {
            selectedSquare = data.selected || { row, col };
            validMoves = data.valid_moves;
            
            fetch(`/get_game_state/${currentGameId}`)
                .then(response => response.json())
                .then(gameData => {
                    updateBoard(gameData.board, gameData.last_move);
                });
        } else {
            selectedSquare = null;
            validMoves = [];
            fetch(`/get_game_state/${currentGameId}`)
                .then(response => response.json())
                .then(gameData => {
                    updateBoard(gameData.board, gameData.last_move);
                });
        }
    })
    .catch(error => console.error('Error:', error));
}

// Make a move
function makeMove(row, col) {
    // Save current state before move
    fetch(`/get_game_state/${currentGameId}`)
        .then(response => response.json())
        .then(gameData => {
            boardHistory.push(JSON.parse(JSON.stringify(gameData)));
        });

    fetch('/api/make_move', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            game_id: currentGameId,
            row: row,
            col: col
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            selectedSquare = null;
            validMoves = [];
            
            // Determine which sound to play
            const wasCaptured = data.last_move && data.captured_pieces && 
                               (data.captured_pieces.white.length + data.captured_pieces.black.length > 
                                capturedPieces.white.length + capturedPieces.black.length);
            
            if (wasCaptured) {
                playSound('capture'); // Play capture sound
            } else {
                playSound('move'); // Play regular move sound
            }
            
            updateBoard(data.board, data.last_move);
            currentPlayer = data.next_player;
            updateTurnIndicator();
            
            if (data.captured_pieces) {
                capturedPieces = data.captured_pieces;
                updateCapturedPieces();
            }
            
            addMoveToHistory(data.last_move);
            analyzeMoveQuality(currentPlayer === 'white' ? 'black' : 'white');
            
            // Update undo button state
            updateUndoButton(data.can_undo);
            
            // Check for check on the opponent
            if (!data.game_over) {
                checkForCheck(data.board, currentPlayer);
            }
            
            if (data.game_over) {
                // Play checkmate sound for checkmate
                if (data.result === 'checkmate') {
                    playSound('checkmate');
                }
                handleGameOver(data);
            } else {
                if (gameType === 'bot' && currentPlayer === 'black') {
                    updateGameStatus('Bot is thinking...');
                } else {
                    updateGameStatus(`${currentPlayer.charAt(0).toUpperCase() + currentPlayer.slice(1)}'s turn`);
                }
            }
        } else {
            // Play illegal move sound
            playSound('illegal');
            alert(data.error || 'Invalid move');
            selectedSquare = null;
            validMoves = [];
            fetch(`/get_game_state/${currentGameId}`)
                .then(response => response.json())
                .then(gameData => {
                    updateBoard(gameData.board, gameData.last_move);
                });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        playSound('illegal');
        alert('Failed to make move. Please try again.');
    });
}

// Update undo button state
function updateUndoButton(canUndo) {
    const undoBtn = document.getElementById('undoBtn');
    if (undoBtn) {
        undoBtn.disabled = !canUndo;
        undoBtn.style.opacity = canUndo ? '1' : '0.5';
    }
}

// Show game options
function showGameOptions() {
    document.getElementById('initialControls').style.display = 'none';
    document.getElementById('gameOptions').style.display = 'block';
}

// Hide game options
function hideGameOptions() {
    document.getElementById('gameOptions').style.display = 'none';
    document.getElementById('initialControls').style.display = 'block';
}

// Start a new game
function startGame(type) {
    gameType = type;
    
    fetch('/start_game', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            type: type,
            difficulty: 3
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentGameId = data.game_id;
            isGameActive = true;
            currentPlayer = 'white';
            moveHistory = [];
            capturedPieces = { white: [], black: [] };
            boardHistory = [];
            moveAnalysis = {
                white: { excellent: 0, good: 0, inaccuracies: 0, mistakes: 0, blunders: 0 },
                black: { excellent: 0, good: 0, inaccuracies: 0, mistakes: 0, blunders: 0 }
            };
            
            updateBoard(data.board);
            updateTurnIndicator();
            updateCapturedPieces();
            updateMoveHistory();
            updateMoveAnalysisDisplay();
            updateUndoButton(false);
            
            document.getElementById('gameOptions').style.display = 'none';
            document.getElementById('gameActiveControls').style.display = 'block';
            document.getElementById('boardContainer').style.display = 'block';
            document.getElementById('gameResultScreen').style.display = 'none';
            
            document.getElementById('whitePlayerName').textContent = 'You (White)';
            document.getElementById('blackPlayerName').textContent = type === 'bot' ? 'Bot (Black)' : 'Opponent (Black)';
            
            // Join socket room for this game
            if (socket) {
                socket.emit('join_game', { game_id: currentGameId });
            }
            
            startGameTimer();
            updateGameStatus('Game started! White to move');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to start game. Please try again.');
    });
}

// Update turn indicator
function updateTurnIndicator() {
    const whiteTurn = document.getElementById('whiteTurn');
    const blackTurn = document.getElementById('blackTurn');
    
    if (currentPlayer === 'white') {
        whiteTurn.textContent = 'Your Turn';
        whiteTurn.classList.add('active');
        blackTurn.textContent = '';
        blackTurn.classList.remove('active');
    } else {
        blackTurn.textContent = gameType === 'bot' ? 'Bot Thinking...' : 'Their Turn';
        blackTurn.classList.add('active');
        whiteTurn.textContent = '';
        whiteTurn.classList.remove('active');
    }
}

// Update captured pieces display
function updateCapturedPieces() {
    const whiteCapturedDiv = document.getElementById('whiteCaptured');
    const blackCapturedDiv = document.getElementById('blackCaptured');
    
    whiteCapturedDiv.innerHTML = '';
    blackCapturedDiv.innerHTML = '';
    
    if (capturedPieces.white.length === 0) {
        whiteCapturedDiv.innerHTML = '<span class="no-captures">No pieces captured</span>';
    } else {
        capturedPieces.white.forEach(piece => {
            const pieceSpan = document.createElement('span');
            pieceSpan.className = 'captured-piece';
            pieceSpan.textContent = pieces[piece.color][piece.name];
            whiteCapturedDiv.appendChild(pieceSpan);
        });
    }
    
    if (capturedPieces.black.length === 0) {
        blackCapturedDiv.innerHTML = '<span class="no-captures">No pieces captured</span>';
    } else {
        capturedPieces.black.forEach(piece => {
            const pieceSpan = document.createElement('span');
            pieceSpan.className = 'captured-piece';
            pieceSpan.textContent = pieces[piece.color][piece.name];
            blackCapturedDiv.appendChild(pieceSpan);
        });
    }
}

// Add move to history
function addMoveToHistory(lastMove) {
    if (!lastMove) return;
    
    const moveHistoryDiv = document.getElementById('moveHistory');
    
    if (moveHistory.length === 0) {
        moveHistoryDiv.innerHTML = '';
    }
    
    const moveNumber = Math.floor(moveHistory.length / 2) + 1;
    const fromSquare = String.fromCharCode(97 + lastMove.initial.col) + (8 - lastMove.initial.row);
    const toSquare = String.fromCharCode(97 + lastMove.final.col) + (8 - lastMove.final.row);
    const moveNotation = `${fromSquare}-${toSquare}`;
    
    moveHistory.push(moveNotation);
    
    if (moveHistory.length % 2 === 1) {
        const moveDiv = document.createElement('div');
        moveDiv.className = 'move-item';
        moveDiv.innerHTML = `<span class="move-number">${moveNumber}.</span> <span class="move-white">${moveNotation}</span>`;
        moveHistoryDiv.appendChild(moveDiv);
    } else {
        const lastMoveDiv = moveHistoryDiv.lastElementChild;
        const blackMoveSpan = document.createElement('span');
        blackMoveSpan.className = 'move-black';
        blackMoveSpan.textContent = moveNotation;
        lastMoveDiv.appendChild(blackMoveSpan);
    }
    
    moveHistoryDiv.scrollTop = moveHistoryDiv.scrollHeight;
}

// Update move history display
function updateMoveHistory() {
    const moveHistoryDiv = document.getElementById('moveHistory');
    
    if (moveHistory.length === 0) {
        moveHistoryDiv.innerHTML = '<div class="no-moves">No moves yet</div>';
    }
}

// Analyze move quality (simulated)
function analyzeMoveQuality(player) {
    const rand = Math.random();
    
    if (rand < 0.3) {
        moveAnalysis[player].excellent++;
    } else if (rand < 0.6) {
        moveAnalysis[player].good++;
    } else if (rand < 0.8) {
        moveAnalysis[player].inaccuracies++;
    } else if (rand < 0.95) {
        moveAnalysis[player].mistakes++;
    } else {
        moveAnalysis[player].blunders++;
    }
    
    updateMoveAnalysisDisplay();
}

// Update move analysis display
function updateMoveAnalysisDisplay() {
    const currentAnalysis = moveAnalysis[currentPlayer === 'white' ? 'black' : 'white'];
    
    document.getElementById('excellentMoves').textContent = currentAnalysis.excellent;
    document.getElementById('goodMoves').textContent = currentAnalysis.good;
    document.getElementById('inaccuracies').textContent = currentAnalysis.inaccuracies;
    document.getElementById('mistakes').textContent = currentAnalysis.mistakes;
    document.getElementById('blunders').textContent = currentAnalysis.blunders;
}

// Start game timer
function startGameTimer() {
    gameStartTime = Date.now();
    
    timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - gameStartTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        
        document.getElementById('gameTimer').textContent = 
            `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }, 1000);
}

// Stop game timer
function stopGameTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

// Update game status
function updateGameStatus(message) {
    document.getElementById('statusMessage').textContent = message;
}

// Handle game over
function handleGameOver(data) {
    isGameActive = false;
    stopGameTimer();
    
    // Play appropriate sound for game ending
    if (data.result === 'checkmate') {
        // Already played in makeMove/handleBotMove, but ensure it plays
        setTimeout(() => playSound('checkmate'), 100);
    }
    
    document.getElementById('gameActiveControls').style.display = 'none';
    document.getElementById('gameOverControls').style.display = 'block';
    
    setTimeout(() => {
        showGameResult(data);
    }, 500);
}

// Show game result
function showGameResult(data) {
    document.getElementById('boardContainer').style.display = 'none';
    document.getElementById('gameResultScreen').style.display = 'block';
    
    let resultText = '';
    if (data.result === 'checkmate') {
        resultText = `Checkmate! ${data.winner.charAt(0).toUpperCase() + data.winner.slice(1)} Wins!`;
    } else if (data.result === 'stalemate') {
        resultText = 'Stalemate - Draw!';
    } else if (data.result === 'resignation') {
        resultText = `Resignation! ${data.winner.charAt(0).toUpperCase() + data.winner.slice(1)} Wins!`;
    } else {
        resultText = 'Game Over';
    }
    
    document.getElementById('resultTitle').textContent = resultText;
    document.getElementById('resultWinner').innerHTML = 
        data.winner !== 'draw' ? 
        `<i class="fas fa-crown"></i> ${data.winner.charAt(0).toUpperCase() + data.winner.slice(1)} Player Wins!` : 
        '<i class="fas fa-handshake"></i> Draw';
    
    displayGameAnalysis();
}

// Display game analysis
function displayGameAnalysis() {
    const whiteAnalysis = moveAnalysis.white;
    const blackAnalysis = moveAnalysis.black;
    
    document.getElementById('whiteExcellent').textContent = whiteAnalysis.excellent;
    document.getElementById('whiteGood').textContent = whiteAnalysis.good;
    document.getElementById('whiteInaccuracies').textContent = whiteAnalysis.inaccuracies;
    document.getElementById('whiteMistakes').textContent = whiteAnalysis.mistakes;
    document.getElementById('whiteBlunders').textContent = whiteAnalysis.blunders;
    
    document.getElementById('blackExcellent').textContent = blackAnalysis.excellent;
    document.getElementById('blackGood').textContent = blackAnalysis.good;
    document.getElementById('blackInaccuracies').textContent = blackAnalysis.inaccuracies;
    document.getElementById('blackMistakes').textContent = blackAnalysis.mistakes;
    document.getElementById('blackBlunders').textContent = blackAnalysis.blunders;
    
    const whiteTotalMoves = whiteAnalysis.excellent + whiteAnalysis.good + whiteAnalysis.inaccuracies + whiteAnalysis.mistakes + whiteAnalysis.blunders;
    const blackTotalMoves = blackAnalysis.excellent + blackAnalysis.good + blackAnalysis.inaccuracies + blackAnalysis.mistakes + blackAnalysis.blunders;
    
    const whiteAccuracy = whiteTotalMoves > 0 ? 
        Math.round(((whiteAnalysis.excellent + whiteAnalysis.good * 0.8) / whiteTotalMoves) * 100) : 0;
    const blackAccuracy = blackTotalMoves > 0 ? 
        Math.round(((blackAnalysis.excellent + blackAnalysis.good * 0.8) / blackTotalMoves) * 100) : 0;
    
    document.getElementById('whiteAccuracy').textContent = whiteAccuracy + '%';
    document.getElementById('blackAccuracy').textContent = blackAccuracy + '%';
    
    const bestPlayer = whiteAccuracy > blackAccuracy ? 'White' : 
                       blackAccuracy > whiteAccuracy ? 'Black' : 'Tie';
    document.getElementById('bestPlayerText').textContent = 
        bestPlayer === 'Tie' ? 'Both players performed equally' : `Best Performance: ${bestPlayer} Player`;
}

// Undo move function - FULLY IMPLEMENTED
function undoMove() {
    if (!currentGameId || !isGameActive) {
        alert('No active game');
        return;
    }
    
    fetch('/api/undo_move', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            game_id: currentGameId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            selectedSquare = null;
            validMoves = [];
            
            updateBoard(data.board);
            currentPlayer = data.next_player;
            updateTurnIndicator();
            
            if (data.captured_pieces) {
                capturedPieces = data.captured_pieces;
                updateCapturedPieces();
            }
            
            // Remove last move(s) from history
            if (gameType === 'bot') {
                // Remove last 2 moves (player + bot)
                if (moveHistory.length >= 2) {
                    moveHistory.pop();
                    moveHistory.pop();
                }
            } else {
                // Remove last move only
                if (moveHistory.length > 0) {
                    moveHistory.pop();
                }
            }
            updateMoveHistory();
            
            // Rebuild move history display
            const moveHistoryDiv = document.getElementById('moveHistory');
            moveHistoryDiv.innerHTML = '';
            
            if (moveHistory.length === 0) {
                moveHistoryDiv.innerHTML = '<div class="no-moves">No moves yet</div>';
            } else {
                for (let i = 0; i < moveHistory.length; i += 2) {
                    const moveNumber = Math.floor(i / 2) + 1;
                    const moveDiv = document.createElement('div');
                    moveDiv.className = 'move-item';
                    moveDiv.innerHTML = `<span class="move-number">${moveNumber}.</span> <span class="move-white">${moveHistory[i]}</span>`;
                    
                    if (i + 1 < moveHistory.length) {
                        const blackMoveSpan = document.createElement('span');
                        blackMoveSpan.className = 'move-black';
                        blackMoveSpan.textContent = moveHistory[i + 1];
                        moveDiv.appendChild(blackMoveSpan);
                    }
                    
                    moveHistoryDiv.appendChild(moveDiv);
                }
            }
            
            updateUndoButton(data.can_undo);
            updateGameStatus(`${currentPlayer.charAt(0).toUpperCase() + currentPlayer.slice(1)}'s turn`);
        } else {
            alert(data.error || 'Cannot undo');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to undo move');
    });
}

// Resign game - FIXED TO SAVE TO DATABASE
function resignGame() {
    if (!currentGameId || !isGameActive) {
        alert('No active game to resign');
        return;
    }
    
    if (confirm('Are you sure you want to resign? This will count as a loss.')) {
        // Call the new API endpoint to handle resignation properly
        fetch('/api/resign_game', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                game_id: currentGameId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Mark game as inactive
                isGameActive = false;
                stopGameTimer();
                
                // Show game over controls
                document.getElementById('gameActiveControls').style.display = 'none';
                document.getElementById('gameOverControls').style.display = 'block';
                
                // Update status message
                updateGameStatus('You resigned the game');
                
                // Show result after a brief delay
                setTimeout(() => {
                    handleGameOver({
                        result: 'resignation',
                        winner: data.winner
                    });
                }, 500);
            } else {
                alert(data.error || 'Failed to resign game');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to resign game. Please try again.');
        });
    }
}

// Play again
function playAgain() {
    location.reload();
}

// View game history
function viewGameHistory() {
    window.location.href = '/game_history';
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        playSound,
        preloadSounds,
        updateVolume,
        checkForCheck,
        makeMove,
        handleBotMove,
        handleGameOver,
        showGameResult
    };
}