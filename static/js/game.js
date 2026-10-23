document.addEventListener('DOMContentLoaded', () => {
    const boardDiv = document.getElementById('board');
    for (let row = 0; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
            const square = document.createElement('div');
            square.style.width = '50px';
            square.style.height = '50px';
            square.style.display = 'inline-block';
            square.style.backgroundColor = (row + col) % 2 === 0 ? '#f0d9b5' : '#b58863';  // Chessboard colors
            square.style.border = '1px solid black';
            square.dataset.row = row;
            square.dataset.col = col;
            square.addEventListener('click', handleClick);
            boardDiv.appendChild(square);
        }
        boardDiv.appendChild(document.createElement('br'));
    }
});

let selectedSquare = null;
let validMoves = [];

function handleClick(event) {
    const row = parseInt(event.target.dataset.row);
    const col = parseInt(event.target.dataset.col);

    if (selectedSquare) {
        fetch('/make_move', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({row, col})
        }).then(res => res.json()).then(data => {
            if (data.success) {
                updateBoard(data.board);
            } else {
                console.error(data.error);
            }
            selectedSquare = null;
            clearHighlights();
        }).catch(err => console.error(err));
    } else {
        fetch('/select_square', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({row, col})
        }).then(res => res.json()).then(data => {
            validMoves = data.valid_moves || [];
            highlightMoves();
            selectedSquare = {row, col};
        }).catch(err => console.error(err));
    }
}

function highlightMoves() {
    validMoves.forEach(move => {
        const square = document.querySelector(`[data-row="${move.row}"][data-col="${move.col}"]`);
        if (square) {
            square.style.backgroundColor = 'yellow';
        }
    });
}

function clearHighlights() {
    document.querySelectorAll('#board div').forEach(sq => {
        const row = parseInt(sq.dataset.row);
        const col = parseInt(sq.dataset.col);
        sq.style.backgroundColor = (row + col) % 2 === 0 ? '#f0d9b5' : '#b58863';
    });
}

function updateBoard(boardData) {
    const pieces = {
        'white': {
            'pawn': '♙',
            'knight': '♘',
            'bishop': '♗',
            'rook': '♖',
            'queen': '♕',
            'king': '♔'
        },
        'black': {
            'pawn': '♟︎',
            'knight': '♞',
            'bishop': '♝',
            'rook': '♜',
            'queen': '♛',
            'king': '♚'
        }
    };

    document.querySelectorAll('#board div').forEach(sq => {
        const row = parseInt(sq.dataset.row);
        const col = parseInt(sq.dataset.col);
        const piece = boardData[row][col];
        sq.innerText = piece ? pieces[piece.color][piece.name] : '';
    });
    clearHighlights();  // Reset highlights after update
}