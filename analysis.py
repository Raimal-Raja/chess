import chess
import chess.engine
import json
from chess_logic import Board, Square, Move

class GameAnalyzer:
    def __init__(self, moves_history, stockfish_path=None):
        self.moves_history = moves_history
        self.stockfish_path = stockfish_path or "/usr/games/stockfish"
        self.engine = None
        
    def _init_engine(self):
        """Lazy initialization of engine"""
        if self.engine is None:
            try:
                self.engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
                return True
            except Exception as e:
                print(f"Warning: Could not initialize Stockfish: {e}")
                return False
        return True

    def _heuristic_analysis(self):
        """
        Heuristic-based analysis when Stockfish is unavailable.
        Analyzes moves based on chess principles.
        """
        analysis = {
            'white': {'blunders': 0, 'mistakes': 0, 'inaccuracies': 0, 'good': 0, 'excellents': 0, 'avg_cp_loss': 0},
            'black': {'blunders': 0, 'mistakes': 0, 'inaccuracies': 0, 'good': 0, 'excellents': 0, 'avg_cp_loss': 0}
        }
        
        if not self.moves_history:
            return analysis
        
        try:
            # Reconstruct the game
            board = Board()
            player = 'white'
            move_count = {'white': 0, 'black': 0}
            
            piece_values = {
                'pawn': 100,
                'knight': 320,
                'bishop': 330,
                'rook': 500,
                'queen': 900,
                'king': 0
            }
            
            for move_data in self.moves_history:
                try:
                    initial_row = move_data['initial']['row']
                    initial_col = move_data['initial']['col']
                    final_row = move_data['final']['row']
                    final_col = move_data['final']['col']
                    
                    # Get the piece being moved
                    piece = board.squares[initial_row][initial_col].piece
                    
                    if not piece:
                        player = 'black' if player == 'white' else 'white'
                        continue
                    
                    # Check if move captures a piece
                    captured = board.squares[final_row][final_col].piece
                    captured_value = piece_values.get(captured.name, 0) if captured else 0
                    
                    # Calculate move to make it on the board
                    initial = Square(initial_row, initial_col)
                    final = Square(final_row, final_col)
                    move = Move(initial, final)
                    
                    # Evaluate the move heuristically
                    move_quality = self._evaluate_move_quality(
                        board, piece, move, captured_value, player
                    )
                    
                    # Categorize the move
                    if move_quality >= 0.9:
                        analysis[player]['excellents'] += 1
                    elif move_quality >= 0.7:
                        analysis[player]['good'] += 1
                    elif move_quality >= 0.5:
                        analysis[player]['inaccuracies'] += 1
                    elif move_quality >= 0.3:
                        analysis[player]['mistakes'] += 1
                    else:
                        analysis[player]['blunders'] += 1
                    
                    # Make the move on the board
                    board.move(piece, move, testing=True)
                    
                    move_count[player] += 1
                    player = 'black' if player == 'white' else 'white'
                    
                except Exception as e:
                    print(f"Error processing move: {e}")
                    player = 'black' if player == 'white' else 'white'
                    continue
            
            # Calculate average CP loss (simulated based on move quality)
            for color in ['white', 'black']:
                if move_count[color] > 0:
                    total_loss = (
                        analysis[color]['inaccuracies'] * 30 +
                        analysis[color]['mistakes'] * 100 +
                        analysis[color]['blunders'] * 300
                    )
                    analysis[color]['avg_cp_loss'] = round(total_loss / move_count[color], 1)
                    
        except Exception as e:
            print(f"Heuristic analysis error: {e}")
            import traceback
            traceback.print_exc()
        
        return analysis
    
    def _evaluate_move_quality(self, board, piece, move, captured_value, player):
        """
        Evaluate move quality based on chess principles.
        Returns a score from 0.0 to 1.0
        """
        score = 0.5  # Base score
        
        piece_values = {
            'pawn': 100,
            'knight': 320,
            'bishop': 330,
            'rook': 500,
            'queen': 900,
            'king': 0
        }
        
        piece_value = piece_values.get(piece.name, 0)
        
        # 1. Capturing pieces is good
        if captured_value > 0:
            if captured_value >= piece_value:
                score += 0.3  # Good trade or capture
            elif captured_value >= piece_value * 0.5:
                score += 0.2  # Decent capture
            else:
                score -= 0.1  # Bad trade
        
        # 2. Center control bonus
        center_squares = [(3, 3), (3, 4), (4, 3), (4, 4)]
        if (move.final.row, move.final.col) in center_squares:
            score += 0.15
        
        # 3. Development bonus (moving knights/bishops from starting position)
        if piece.name in ['knight', 'bishop']:
            starting_row = 0 if player == 'black' else 7
            if move.initial.row == starting_row:
                score += 0.1
        
        # 4. King safety - castling is good
        if piece.name == 'king':
            # Detect castling (king moves 2 squares horizontally)
            if abs(move.final.col - move.initial.col) == 2:
                score += 0.3
            # King moving in opening/middlegame is risky
            elif len(board.moves_history) < 20:
                score -= 0.15
        
        # 5. Pawn structure
        if piece.name == 'pawn':
            # Advanced pawns are good
            advancement = move.final.row if player == 'white' else 7 - move.final.row
            if advancement >= 5:
                score += 0.15
            # Doubled pawns are bad (check if there's already a pawn in this column)
            for row in range(8):
                if row != move.final.row:
                    square_piece = board.squares[row][move.final.col].piece
                    if square_piece and square_piece.name == 'pawn' and square_piece.color == player:
                        score -= 0.1
                        break
        
        # 6. Check if move puts own pieces in danger
        # Calculate if the destination square is attacked
        opponent_color = 'black' if player == 'white' else 'white'
        is_attacked = self._is_square_attacked(board, move.final.row, move.final.col, opponent_color)
        
        if is_attacked and captured_value == 0:
            # Moving into danger without capturing
            score -= 0.2
        
        # 7. Developing pieces is good in opening
        if len(board.moves_history) < 15 and piece.name in ['knight', 'bishop']:
            score += 0.1
        
        # Clamp score between 0 and 1
        return max(0.0, min(1.0, score))
    
    def _is_square_attacked(self, board, row, col, by_color):
        """Check if a square is attacked by a specific color"""
        # Simplified attack detection
        directions = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
        knight_moves = [(-2,-1), (-2,1), (-1,-2), (-1,2), (1,-2), (1,2), (2,-1), (2,1)]
        
        # Check knight attacks
        for dr, dc in knight_moves:
            r, c = row + dr, col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                piece = board.squares[r][c].piece
                if piece and piece.name == 'knight' and piece.color == by_color:
                    return True
        
        # Check sliding pieces
        for dr, dc in directions:
            for dist in range(1, 8):
                r, c = row + dr * dist, col + dc * dist
                if not (0 <= r < 8 and 0 <= c < 8):
                    break
                piece = board.squares[r][c].piece
                if piece:
                    if piece.color == by_color:
                        if piece.name in ['queen', 'rook', 'bishop', 'king']:
                            return True
                    break
        
        # Check pawn attacks
        pawn_direction = -1 if by_color == 'white' else 1
        for dc in [-1, 1]:
            r, c = row + pawn_direction, col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                piece = board.squares[r][c].piece
                if piece and piece.name == 'pawn' and piece.color == by_color:
                    return True
        
        return False

    def analyze(self):
        """Main analysis function - tries Stockfish first, falls back to heuristic"""
        # Try Stockfish analysis first
        if self._init_engine():
            try:
                return self._stockfish_analysis()
            except Exception as e:
                print(f"Stockfish analysis failed: {e}")
                if self.engine:
                    try:
                        self.engine.quit()
                    except:
                        pass
                self.engine = None
        
        # Fallback to heuristic analysis
        print("Using heuristic-based analysis")
        return self._heuristic_analysis()

    def _stockfish_analysis(self):
        """Stockfish-based analysis"""
        analysis = {
            'white': {'blunders': 0, 'mistakes': 0, 'inaccuracies': 0, 'good': 0, 'excellents': 0, 'avg_cp_loss': 0},
            'black': {'blunders': 0, 'mistakes': 0, 'inaccuracies': 0, 'good': 0, 'excellents': 0, 'avg_cp_loss': 0}
        }
        
        board = chess.Board()
        player = 'white'
        cp_losses = {'white': [], 'black': []}
        
        for move in self.moves_history:
            try:
                initial_col = chr(ord('a') + move['initial']['col'])
                initial_row = 8 - move['initial']['row']
                final_col = chr(ord('a') + move['final']['col'])
                final_row = 8 - move['final']['row']
                uci_move = f"{initial_col}{initial_row}{final_col}{final_row}"
                
                # Analyze position before move
                info = self.engine.analyse(board, chess.engine.Limit(time=0.1, depth=12))
                best_move = info["pv"][0].uci() if info.get("pv") else None
                best_score = info["score"].relative.score(mate_score=10000) if info.get("score") else 0
                
                if uci_move == best_move:
                    analysis[player]['excellents'] += 1
                else:
                    # Make the move
                    board.push_uci(uci_move)
                    
                    # Analyze position after move
                    info_after = self.engine.analyse(board, chess.engine.Limit(time=0.1, depth=12))
                    after_score = info_after["score"].relative.score(mate_score=10000) if info_after.get("score") else 0
                    
                    cp_loss = abs((best_score or 0) - (after_score or 0))
                    cp_losses[player].append(cp_loss)
                    
                    if cp_loss > 300:
                        analysis[player]['blunders'] += 1
                    elif cp_loss > 100:
                        analysis[player]['mistakes'] += 1
                    elif cp_loss > 50:
                        analysis[player]['inaccuracies'] += 1
                    elif cp_loss > 20:
                        analysis[player]['good'] += 1
                    else:
                        analysis[player]['excellents'] += 1
                
                if board.is_legal(chess.Move.from_uci(uci_move)):
                    player = 'black' if player == 'white' else 'white'
                
            except Exception as e:
                print(f"Analysis error on move {uci_move}: {e}")
                # Try to continue
                try:
                    board.push_uci(uci_move)
                    player = 'black' if player == 'white' else 'white'
                except:
                    pass
                continue
        
        # Calculate average CP loss
        for color in ['white', 'black']:
            if cp_losses[color]:
                analysis[color]['avg_cp_loss'] = round(sum(cp_losses[color]) / len(cp_losses[color]), 1)
        
        if self.engine:
            try:
                self.engine.quit()
            except:
                pass
        
        return analysis