import copy
import random

piece_values = {
    'pawn': 100,
    'knight': 320,
    'bishop': 330,
    'rook': 500,
    'queen': 900,
    'king': 20000
}

# Opening  - Based on Magnus Carlsen, Hikaru Nakamura games
OPENING_BOOK = {
    # Starting positions
    '': [
        {'from': (6, 4), 'to': (4, 4)},  # e4 - King's Pawn (most common)
        {'from': (6, 3), 'to': (4, 3)},  # d4 - Queen's Pawn
        {'from': (7, 6), 'to': (5, 5)},  # Nf3 - Reti Opening
        {'from': (6, 2), 'to': (4, 2)},  # c4 - English Opening
    ],
    
    # After 1.e4 (Magnus's favorite)
    'e2e4': [
        {'from': (1, 4), 'to': (3, 4)},  # e5 (Classical)
        {'from': (1, 2), 'to': (3, 2)},  # c5 (Sicilian Defense - Hikaru's specialty)
        {'from': (1, 4), 'to': (2, 4)},  # e6 (French Defense)
        {'from': (1, 6), 'to': (2, 6)},  # Nf6 (Alekhine Defense)
    ],
    
    # After 1.d4
    'd2d4': [
        {'from': (1, 3), 'to': (3, 3)},  # d5 (Queen's Gambit)
        {'from': (0, 6), 'to': (2, 5)},  # Nf6 (Indian Defenses)
        {'from': (1, 5), 'to': (2, 5)},  # f5 (Dutch Defense)
    ],
    
    # Ruy Lopez (Spanish Opening) - Magnus's weapon
    'e2e4,e7e5': [
        {'from': (7, 6), 'to': (5, 5)},  # Nf3
    ],
    'e2e4,e7e5,g1f3': [
        {'from': (0, 1), 'to': (2, 2)},  # Nc6
    ],
    'e2e4,e7e5,g1f3,b8c6': [
        {'from': (7, 5), 'to': (4, 2)},  # Bb5 (Ruy Lopez)
    ],
    
    # Sicilian Defense - Najdorf (Hikaru's favorite)
    'e2e4,c7c5': [
        {'from': (7, 6), 'to': (5, 5)},  # Nf3
    ],
    'e2e4,c7c5,g1f3': [
        {'from': (1, 3), 'to': (3, 3)},  # d6
        {'from': (0, 1), 'to': (2, 2)},  # Nc6
        {'from': (1, 4), 'to': (3, 4)},  # e6
    ],
    'e2e4,c7c5,g1f3,d7d6': [
        {'from': (6, 3), 'to': (4, 3)},  # d4
    ],
    'e2e4,c7c5,g1f3,d7d6,d2d4': [
        {'from': (3, 2), 'to': (4, 3)},  # cxd4
    ],
    'e2e4,c7c5,g1f3,d7d6,d2d4,c5d4': [
        {'from': (5, 5), 'to': (4, 3)},  # Nxd4
    ],
    'e2e4,c7c5,g1f3,d7d6,d2d4,c5d4,f3d4': [
        {'from': (0, 6), 'to': (2, 5)},  # Nf6
    ],
    
    # Queen's Gambit - Magnus's solid choice
    'd2d4,d7d5': [
        {'from': (6, 2), 'to': (4, 2)},  # c4 (Queen's Gambit)
    ],
    'd2d4,d7d5,c2c4': [
        {'from': (3, 3), 'to': (4, 2)},  # dxc4 (Accepted)
        {'from': (1, 4), 'to': (2, 4)},  # e6 (Declined)
        {'from': (1, 2), 'to': (2, 2)},  # c6 (Slav Defense)
    ],
    
    # King's Indian Defense
    'd2d4,g8f6': [
        {'from': (6, 2), 'to': (4, 2)},  # c4
    ],
    'd2d4,g8f6,c2c4': [
        {'from': (1, 6), 'to': (2, 6)},  # g6 (King's Indian)
    ],
    'd2d4,g8f6,c2c4,g7g6': [
        {'from': (7, 1), 'to': (5, 2)},  # Nc3
    ],
    'd2d4,g8f6,c2c4,g7g6,b1c3': [
        {'from': (1, 5), 'to': (2, 6)},  # Bg7
    ],
    
    # Italian Game - Classical
    'e2e4,e7e5,g1f3,b8c6,f1c4': [
        {'from': (0, 5), 'to': (3, 2)},  # Bc5
        {'from': (0, 6), 'to': (2, 5)},  # Nf6
    ],
    
    # French Defense
    'e2e4,e7e6': [
        {'from': (6, 3), 'to': (4, 3)},  # d4
    ],
    'e2e4,e7e6,d2d4': [
        {'from': (1, 3), 'to': (3, 3)},  # d5
    ],
    'e2e4,e7e6,d2d4,d7d5': [
        {'from': (7, 1), 'to': (5, 2)},  # Nc3 (Classical)
        {'from': (4, 4), 'to': (3, 4)},  # e5 (Advance)
    ],
    
    # Caro-Kann Defense - Magnus's defensive weapon
    'e2e4,c7c6': [
        {'from': (6, 3), 'to': (4, 3)},  # d4
    ],
    'e2e4,c7c6,d2d4': [
        {'from': (1, 3), 'to': (3, 3)},  # d5
    ],
    
    # London System - Solid opening
    'd2d4,d7d5,c1f4': [
        {'from': (0, 6), 'to': (2, 5)},  # Nf6
    ],
    'd2d4,g8f6,c1f4': [
        {'from': (1, 3), 'to': (3, 3)},  # d5
        {'from': (1, 4), 'to': (2, 4)},  # e6
    ],
}

# position value tables (piece-square tables)
pawn_table = [
    [0,   0,   0,   0,   0,   0,   0,   0],
    [50,  50,  50,  50,  50,  50,  50,  50],
    [10,  10,  20,  30,  30,  20,  10,  10],
    [5,   5,   10,  27,  27,  10,  5,   5],
    [0,   0,   0,   25,  25,  0,   0,   0],
    [5,   -5,  -10, 0,   0,   -10, -5,  5],
    [5,   10,  10,  -25, -25, 10,  10,  5],
    [0,   0,   0,   0,   0,   0,   0,   0]
]

knight_table = [
    [-50, -40, -30, -30, -30, -30, -40, -50],
    [-40, -20, 0,   0,   0,   0,   -20, -40],
    [-30, 0,   10,  15,  15,  10,  0,   -30],
    [-30, 5,   15,  20,  20,  15,  5,   -30],
    [-30, 0,   15,  20,  20,  15,  0,   -30],
    [-30, 5,   10,  15,  15,  10,  5,   -30],
    [-40, -20, 0,   5,   5,   0,   -20, -40],
    [-50, -40, -20, -30, -30, -20, -40, -50]
]

bishop_table = [
    [-20, -10, -10, -10, -10, -10, -10, -20],
    [-10, 0,   0,   0,   0,   0,   0,   -10],
    [-10, 0,   5,   10,  10,  5,   0,   -10],
    [-10, 5,   5,   10,  10,  5,   5,   -10],
    [-10, 0,   10,  10,  10,  10,  0,   -10],
    [-10, 10,  10,  10,  10,  10,  10,  -10],
    [-10, 5,   0,   0,   0,   0,   5,   -10],
    [-20, -10, -40, -10, -10, -40, -10, -20]
]

rook_table = [
    [0,   0,   0,   0,   0,   0,   0,   0],
    [5,   10,  10,  10,  10,  10,  10,  5],
    [-5,  0,   0,   0,   0,   0,   0,   -5],
    [-5,  0,   0,   0,   0,   0,   0,   -5],
    [-5,  0,   0,   0,   0,   0,   0,   -5],
    [-5,  0,   0,   0,   0,   0,   0,   -5],
    [-5,  0,   0,   0,   0,   0,   0,   -5],
    [0,   0,   0,   5,   5,   0,   0,   0]
]

queen_table = [
    [-20, -10, -10, -5,  -5,  -10, -10, -20],
    [-10, 0,   0,   0,   0,   0,   0,   -10],
    [-10, 0,   5,   5,   5,   5,   0,   -10],
    [-5,  0,   5,   5,   5,   5,   0,   -5],
    [0,   0,   5,   5,   5,   5,   0,   -5],
    [-10, 5,   5,   5,   5,   5,   0,   -10],
    [-10, 0,   5,   0,   0,   0,   0,   -10],
    [-20, -10, -10, -5,  -5,  -10, -10, -20]
]

king_middle_game = [
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-20, -30, -30, -40, -40, -30, -30, -20],
    [-10, -20, -20, -20, -20, -20, -20, -10],
    [20,  20,  0,   0,   0,   0,   20,  20],
    [20,  30,  10,  0,   0,   10,  30,  20]
]

king_end_game = [
    [-50, -40, -30, -20, -20, -30, -40, -50],
    [-30, -20, -10, 0,   0,   -10, -20, -30],
    [-30, -10, 20,  30,  30,  20,  -10, -30],
    [-30, -10, 30,  40,  40,  30,  -10, -30],
    [-30, -10, 30,  40,  40,  30,  -10, -30],
    [-30, -10, 20,  30,  30,  20,  -10, -30],
    [-30, -30, 0,   0,   0,   0,   -30, -30],
    [-50, -30, -30, -30, -30, -30, -30, -50]
]

class ChessAI:
    def __init__(self, board, color):
        self.board = board
        self.color = color
        self.opponent_color = 'white' if color == 'black' else 'black'
        self.nodes_searched = 0
        
    def get_opening_move(self):
        """Check if we can use opening book - EXPANDED"""
        if len(self.board.moves_history) > 12:  # Use book for first 12 moves
            return None
        
        # Build move history string
        move_str = ''
        for i, move in enumerate(self.board.moves_history):
            cols = 'abcdefgh'
            rows = '87654321'
            from_sq = cols[move.initial.col] + rows[move.initial.row]
            to_sq = cols[move.final.col] + rows[move.final.row]
            if i > 0:
                move_str += ','
            move_str += from_sq + to_sq
        
        # Check if we have book moves for this position
        if move_str in OPENING_BOOK:
            book_moves = OPENING_BOOK[move_str]
            # Pick a random move from book to add variety
            book_move = random.choice(book_moves)
            
            # Convert to Move object
            from chess_logic import Square, Move
            initial = Square(book_move['from'][0], book_move['from'][1])
            final = Square(book_move['to'][0], book_move['to'][1])
            move = Move(initial, final)
            
            # Verify move is legal
            piece = self.board.squares[initial.row][initial.col].piece
            if piece and piece.color == self.color:
                self.board.calc_moves(piece, initial.row, initial.col)
                if move in piece.moves:
                    print(f"Opening book move: {from_sq}{to_sq}")
                    return move
        
        return None
        
    def is_endgame(self):
        """Detect endgame - FASTER"""
        piece_count = 0
        queen_count = 0
        for row in range(8):
            for col in range(8):
                piece = self.board.squares[row][col].piece
                if piece and piece.name != 'king':
                    piece_count += 1
                    if piece.name == 'queen':
                        queen_count += 1
        return piece_count <= 6 or queen_count == 0

    def count_attackers_and_defenders(self, row, col, color):
        """OPTIMIZED: Count how many pieces attack and defend a square"""
        attackers = 0
        defenders = 0
        
        # Simplified - only check immediate threats
        directions = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
        knight_moves = [(-2,-1), (-2,1), (-1,-2), (-1,2), (1,-2), (1,2), (2,-1), (2,1)]
        
        # Check knight attacks
        for dr, dc in knight_moves:
            r, c = row + dr, col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                piece = self.board.squares[r][c].piece
                if piece and piece.name == 'knight':
                    if piece.color == color:
                        defenders += 1
                    else:
                        attackers += 1
        
        # Check sliding pieces (simplified)
        for dr, dc in directions:
            for dist in range(1, 8):
                r, c = row + dr * dist, col + dc * dist
                if not (0 <= r < 8 and 0 <= c < 8):
                    break
                piece = self.board.squares[r][c].piece
                if piece:
                    if piece.name in ['queen', 'rook', 'bishop']:
                        if piece.color == color:
                            defenders += 1
                        else:
                            attackers += 1
                    break
        
        return attackers, defenders

    def is_piece_hanging(self, row, col):
        """Check if a piece is undefended or hanging"""
        piece = self.board.squares[row][col].piece
        if not piece:
            return False
        
        attackers, defenders = self.count_attackers_and_defenders(row, col, piece.color)
        
        # Piece is hanging if attacked but not defended
        return attackers > 0 and defenders == 0

    def evaluate_king_safety(self, color):
        """OPTIMIZED: Faster king safety evaluation"""
        from chess_logic import King, Pawn
        
        safety_score = 0
        
        # Find king position (cache this if possible)
        king_row, king_col = None, None
        for row in range(8):
            for col in range(8):
                piece = self.board.squares[row][col].piece
                if isinstance(piece, King) and piece.color == color:
                    king_row, king_col = row, col
                    break
            if king_row is not None:
                break
        
        if king_row is None:
            return 0
        
        # Simplified pawn shield check
        direction = -1 if color == 'white' else 1
        pawn_shield = 0
        
        for col_offset in [-1, 0, 1]:
            check_col = king_col + col_offset
            check_row = king_row + direction
            
            if 0 <= check_col < 8 and 0 <= check_row < 8:
                piece = self.board.squares[check_row][check_col].piece
                if isinstance(piece, Pawn) and piece.color == color:
                    pawn_shield += 1
        
        safety_score += pawn_shield * 20
        
        # Penalty for king in center (only in middlegame)
        if not self.is_endgame() and 2 <= king_col <= 5:
            safety_score -= 30
        
        return safety_score

    def evaluate_piece_activity(self, color):
        """OPTIMIZED: Faster piece activity evaluation"""
        activity_score = 0
        
        # Only check developed pieces (not pawns/king)
        for row in range(8):
            for col in range(8):
                piece = self.board.squares[row][col].piece
                if piece and piece.color == color and piece.name in ['knight', 'bishop', 'rook', 'queen']:
                    # Simple mobility estimate without full calculation
                    if piece.name == 'knight':
                        # Knights in center are more active
                        center_distance = abs(row - 3.5) + abs(col - 3.5)
                        activity_score += (7 - center_distance) * 3
                    elif piece.name == 'bishop':
                        # Bishops on long diagonals
                        if (row == col) or (row + col == 7):
                            activity_score += 10
                    elif piece.name == 'rook':
                        # Rooks on open files (simplified check)
                        has_pawn = False
                        for r in range(8):
                            p = self.board.squares[r][col].piece
                            if p and p.name == 'pawn':
                                has_pawn = True
                                break
                        if not has_pawn:
                            activity_score += 15  # Open file bonus
        
        return activity_score

    def evaluate_pawn_structure(self, color):
        """OPTIMIZED: Faster pawn structure evaluation"""
        from chess_logic import Pawn
        
        structure_score = 0
        pawn_files = {}
        
        # Collect pawns by file
        for row in range(8):
            for col in range(8):
                piece = self.board.squares[row][col].piece
                if isinstance(piece, Pawn) and piece.color == color:
                    if col not in pawn_files:
                        pawn_files[col] = []
                    pawn_files[col].append(row)
        
        for col, rows in pawn_files.items():
            # Penalty for doubled pawns
            if len(rows) > 1:
                structure_score -= 10 * (len(rows) - 1)
            
            # Check for isolated pawns
            has_neighbor = (col - 1 in pawn_files) or (col + 1 in pawn_files)
            if not has_neighbor:
                structure_score -= 15
            
            # Bonus for advanced pawns
            for row in rows:
                advancement = row if color == 'white' else 7 - row
                if advancement >= 5:  # Advanced pawn
                    structure_score += advancement * 5
        
        return structure_score

    def evaluate_threats(self, color):
        """OPTIMIZED: Faster threat evaluation"""
        threat_score = 0
        
        # Quick check for hanging pieces (sample only major pieces)
        for row in range(8):
            for col in range(8):
                piece = self.board.squares[row][col].piece
                if piece and piece.name in ['queen', 'rook', 'bishop', 'knight']:
                    attackers, defenders = self.count_attackers_and_defenders(row, col, piece.color)
                    
                    if piece.color != color and attackers > defenders:
                        # Enemy piece is hanging - bonus
                        threat_score += piece_values.get(piece.name, 0) // 4
                    elif piece.color == color and attackers > defenders:
                        # Our piece is hanging - penalty
                        threat_score -= piece_values.get(piece.name, 0) // 4
        
        return threat_score

    def evaluate(self):
        """OPTIMIZED evaluation - faster calculations"""
        score = 0
        is_endgame = self.is_endgame()
        
        # Material and position evaluation
        for row in range(8):
            for col in range(8):
                piece = self.board.squares[row][col].piece
                if piece:
                    material = piece_values.get(piece.name, 0)
                    piece_row = row if piece.color == 'white' else 7 - row
                    position_bonus = 0
                    
                    if piece.name == 'pawn':
                        position_bonus = pawn_table[piece_row][col]
                    elif piece.name == 'knight':
                        position_bonus = knight_table[piece_row][col]
                    elif piece.name == 'bishop':
                        position_bonus = bishop_table[piece_row][col]
                    elif piece.name == 'rook':
                        position_bonus = rook_table[piece_row][col]
                    elif piece.name == 'queen':
                        position_bonus = queen_table[piece_row][col]
                    elif piece.name == 'king':
                        position_bonus = king_end_game[piece_row][col] if is_endgame else king_middle_game[piece_row][col]
                    
                    piece_score = material + position_bonus
                    score += piece_score if piece.color == self.color else -piece_score
        
        # Reduced weight strategic factors for speed
        my_king_safety = self.evaluate_king_safety(self.color)
        opponent_king_safety = self.evaluate_king_safety(self.opponent_color)
        score += my_king_safety * 0.3 - opponent_king_safety * 0.2
        
        my_activity = self.evaluate_piece_activity(self.color)
        opponent_activity = self.evaluate_piece_activity(self.opponent_color)
        score += my_activity * 0.2 - opponent_activity * 0.15
        
        my_pawn_structure = self.evaluate_pawn_structure(self.color)
        opponent_pawn_structure = self.evaluate_pawn_structure(self.opponent_color)
        score += my_pawn_structure * 0.3 - opponent_pawn_structure * 0.2
        
        threat_evaluation = self.evaluate_threats(self.color)
        score += threat_evaluation * 0.4
        
        return score

    def order_moves(self, moves):
        """ENHANCED move ordering with tactical priorities"""
        from chess_logic import King
        
        scored_moves = []
        
        for move in moves:
            score = 0
            target = self.board.squares[move.final.row][move.final.col].piece
            moving_piece = self.board.squares[move.initial.row][move.initial.col].piece
            
            # MVV-LVA: Most Valuable Victim - Least Valuable Attacker
            if target:
                victim_value = piece_values.get(target.name, 0)
                attacker_value = piece_values.get(moving_piece.name, 0)
                score += 10000 + victim_value * 10 - attacker_value
            
            # Bonus for checks
            temp_board = copy.deepcopy(self.board)
            temp_piece = temp_board.squares[move.initial.row][move.initial.col].piece
            temp_board.move(temp_piece, move, testing=True)
            
            if temp_board.in_check_king(self.opponent_color):
                score += 5000  # High priority for checks
            
            # Bonus for attacking king zone
            opponent_king_pos = None
            for row in range(8):
                for col in range(8):
                    piece = temp_board.squares[row][col].piece
                    if isinstance(piece, King) and piece.color == self.opponent_color:
                        opponent_king_pos = (row, col)
                        break
                if opponent_king_pos:
                    break
            
            if opponent_king_pos:
                king_row, king_col = opponent_king_pos
                distance_to_king = abs(move.final.row - king_row) + abs(move.final.col - king_col)
                if distance_to_king <= 2:
                    score += 200  # Bonus for attacking near king
            
            # Center control bonus
            center_distance = abs(move.final.row - 3.5) + abs(move.final.col - 3.5)
            score += (7 - center_distance) * 5
            
            # Penalty for moving into attacked squares
            if not target:  # Only check if not capturing
                attackers, defenders = self.count_attackers_and_defenders(
                    move.final.row, move.final.col, moving_piece.color
                )
                if attackers > defenders:
                    score -= 1000  # Avoid moving into danger
            
            scored_moves.append((score, move))
        
        scored_moves.sort(reverse=True, key=lambda x: x[0])
        return [move for _, move in scored_moves]

    def minimax(self, depth, alpha, beta, maximizing):
        """OPTIMIZED minimax with aggressive pruning"""
        self.nodes_searched += 1
        
        if depth == 0:
            return self.evaluate()
        
        moves = self.get_all_moves(self.color if maximizing else self.opponent_color)
        
        if not moves:
            if self.board.in_check_king(self.color if maximizing else self.opponent_color):
                return -100000 if maximizing else 100000
            return 0
        
        moves = self.order_moves(moves)
        
        # MORE aggressive move reduction for speed
        if depth >= 3:
            max_moves = 10
        elif depth >= 2:
            max_moves = 15
        else:
            max_moves = 20
        moves = moves[:max_moves]
        
        if maximizing:
            max_eval = -float('inf')
            for move in moves:
                temp_board = copy.deepcopy(self.board)
                piece = temp_board.squares[move.initial.row][move.initial.col].piece
                temp_board.move(piece, move, testing=True)
                
                temp_ai = ChessAI(temp_board, self.color)
                eval = temp_ai.minimax(depth - 1, alpha, beta, False)
                
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break  # Beta cutoff
            
            return max_eval
        else:
            min_eval = float('inf')
            for move in moves:
                temp_board = copy.deepcopy(self.board)
                piece = temp_board.squares[move.initial.row][move.initial.col].piece
                temp_board.move(piece, move, testing=True)
                
                temp_ai = ChessAI(temp_board, self.color)
                eval = temp_ai.minimax(depth - 1, alpha, beta, True)
                
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha:
                    break  # Alpha cutoff
            
            return min_eval

    def get_all_moves(self, color):
        """Get all legal moves - CACHED"""
        moves = []
        for row in range(8):
            for col in range(8):
                piece = self.board.squares[row][col].piece
                if piece and piece.color == color:
                    self.board.calc_moves(piece, row, col, bool=True)
                    moves.extend(piece.moves)
        return moves

    def get_best_move(self, depth=3):
        """Find best move with ENHANCED attacking/defensive play"""
        self.nodes_searched = 0
        
        # Try opening book first
        book_move = self.get_opening_move()
        if book_move:
            print(f"Using opening book move")
            return book_move
        
        best_move = None
        best_value = -float('inf')
        
        moves = self.get_all_moves(self.color)
        if not moves:
            return None
        
        moves = self.order_moves(moves)
        
        # Search top moves only for speed
        search_moves = min(18, len(moves))
        
        print(f"Evaluating {search_moves} candidate moves...")
        
        for i, move in enumerate(moves[:search_moves]):
            temp_board = copy.deepcopy(self.board)
            piece = temp_board.squares[move.initial.row][move.initial.col].piece
            temp_board.move(piece, move, testing=True)
            
            temp_ai = ChessAI(temp_board, self.opponent_color)
            board_value = -temp_ai.minimax(depth - 1, -float('inf'), float('inf'), True)
            
            # Add randomness for variety (small amount)
            board_value += random.uniform(-5, 5)
            
            if board_value > best_value:
                best_value = board_value
                best_move = move
                
                # Get move description
                from_square = f"{chr(97 + move.initial.col)}{8 - move.initial.row}"
                to_square = f"{chr(97 + move.final.col)}{8 - move.final.row}"
                piece_name = piece.name.capitalize()
                
                # Determine move type
                target = self.board.squares[move.final.row][move.final.col].piece
                if target:
                    move_type = f"ATTACKING - {piece_name} captures {target.name}"
                elif self.is_piece_hanging(move.initial.row, move.initial.col):
                    move_type = f"DEFENSIVE - {piece_name} moves to safety"
                else:
                    # Check if this move attacks opponent pieces
                    temp_board2 = copy.deepcopy(self.board)
                    temp_piece2 = temp_board2.squares[move.initial.row][move.initial.col].piece
                    temp_board2.move(temp_piece2, move, testing=True)
                    
                    attacks_enemy = False
                    temp_board2.calc_moves(temp_piece2, move.final.row, move.final.col, bool=False)
                    for m in temp_piece2.moves:
                        if temp_board2.squares[m.final.row][m.final.col].piece:
                            attacks_enemy = True
                            break
                    
                    if attacks_enemy:
                        move_type = f"AGGRESSIVE - {piece_name} attacks enemy position"
                    elif temp_board2.in_check_king(self.opponent_color):
                        move_type = f"ATTACKING - {piece_name} gives check!"
                    else:
                        move_type = f"POSITIONAL - {piece_name} improves position"
                
                print(f"  [{i+1}] {from_square}->{to_square}: {move_type} (eval: {board_value:.1f})")
        
        if best_move:
            from_square = f"{chr(97 + best_move.initial.col)}{8 - best_move.initial.row}"
            to_square = f"{chr(97 + best_move.final.col)}{8 - best_move.final.row}"
            print(f"\nBest move selected: {from_square}->{to_square}")
            print(f"Nodes searched: {self.nodes_searched}, Evaluation: {best_value:.1f}")
        
        return best_move