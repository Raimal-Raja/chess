import copy

ROWS = 8
COLS = 8

class Piece:
    def __init__(self, name, color, value):
        self.name = name
        self.color = color
        self.value = value * (1 if color == 'white' else -1)
        self.moves = []
        self.moved = False

    def add_move(self, move):
        self.moves.append(move)

    def clear_moves(self):
        self.moves = []

    def to_dict(self):
        return {
            'name': self.name,
            'color': self.color,
            'moved': self.moved
        }

class Pawn(Piece):
    def __init__(self, color):
        super().__init__('pawn', color, 1.0)
        self.dir = -1 if color == 'white' else 1
        self.en_passant = False

class Knight(Piece):
    def __init__(self, color):
        super().__init__('knight', color, 3.0)

class Bishop(Piece):
    def __init__(self, color):
        super().__init__('bishop', color, 3.001)

class Rook(Piece):
    def __init__(self, color):
        super().__init__('rook', color, 5.0)

class Queen(Piece):
    def __init__(self, color):
        super().__init__('queen', color, 9.0)

class King(Piece):
    def __init__(self, color):
        super().__init__('king', color, 10000.0)
        self.left_rook = None
        self.right_rook = None

class Square:
    ALPHACOLS = {0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e', 5: 'f', 6: 'g', 7: 'h'}
    
    def __init__(self, row, col, piece=None):
        self.row = row
        self.col = col
        self.piece = piece

    def has_piece(self):
        return self.piece is not None

    def isempty(self):
        return not self.has_piece()

    def has_team_piece(self, color):
        return self.has_piece() and self.piece.color == color

    def has_enemy_piece(self, color):
        return self.has_piece() and self.piece.color != color

    def isempty_or_enemy(self, color):
        return self.isempty() or self.has_enemy_piece(color)

    @staticmethod
    def in_range(*args):
        for arg in args:
            if arg < 0 or arg > 7:
                return False
        return True
    
    def to_dict(self):
        return {'row': self.row, 'col': self.col}

class Move:
    def __init__(self, initial, final):
        self.initial = initial
        self.final = final

    def __eq__(self, other):
        return self.initial.row == other.initial.row and \
               self.initial.col == other.initial.col and \
               self.final.row == other.final.row and \
               self.final.col == other.final.col
               
    def to_dict(self):
        return {'initial': self.initial.to_dict(), 'final': self.final.to_dict()}

class Board:
    def __init__(self):
        self.squares = [[Square(row, col) for col in range(COLS)] for row in range(ROWS)]
        self.last_move = None
        self.moves_history = []
        self._king_positions = {'white': None, 'black': None}  # Cache king positions
        self._add_pieces('white')
        self._add_pieces('black')

    def move(self, piece, move, testing=False):
        initial = move.initial
        final = move.final

        en_passant_empty = self.squares[final.row][final.col].isempty()

        self.squares[initial.row][initial.col].piece = None
        self.squares[final.row][final.col].piece = piece
        
        # Update cached king position
        if isinstance(piece, King):
            self._king_positions[piece.color] = (final.row, final.col)

        if isinstance(piece, Pawn):
            diff = final.col - initial.col
            if diff != 0 and en_passant_empty:
                self.squares[initial.row][initial.col + diff].piece = None
            self.check_promotion(piece, final)

        if isinstance(piece, King):
            if self.castling(initial, final) and not testing:
                diff = final.col - initial.col
                rook = piece.left_rook if (diff < 0) else piece.right_rook
                self.move(rook, rook.moves[-1])

        piece.moved = True
        piece.clear_moves()
        self.last_move = move
        if not testing:
            self.moves_history.append(move)

    def valid_move(self, piece, move):
        return move in piece.moves

    def check_promotion(self, piece, final):
        if final.row == 0 or final.row == 7:
            self.squares[final.row][final.col].piece = Queen(piece.color)

    def castling(self, initial, final):
        return abs(initial.col - final.col) == 2

    def set_true_en_passant(self, piece):
        if not isinstance(piece, Pawn):
            return

        for row in range(ROWS):
            for col in range(COLS):
                if isinstance(self.squares[row][col].piece, Pawn):
                    self.squares[row][col].piece.en_passant = False
        
        piece.en_passant = True

    def in_check(self, piece, move):
        """OPTIMIZED: Faster check detection"""
        temp_piece = copy.deepcopy(piece)
        temp_board = copy.deepcopy(self)
        temp_board.move(temp_piece, move, testing=True)
        
        # Find king position faster using cached position
        king_pos = None
        if isinstance(temp_piece, King):
            king_pos = (move.final.row, move.final.col)
        else:
            # Use cached king position if available
            if temp_board._king_positions[piece.color]:
                king_pos = temp_board._king_positions[piece.color]
            else:
                # Fallback: search for king
                for row in range(ROWS):
                    for col in range(COLS):
                        p = temp_board.squares[row][col].piece
                        if isinstance(p, King) and p.color == piece.color:
                            king_pos = (row, col)
                            break
                    if king_pos:
                        break
        
        if not king_pos:
            return False
        
        king_row, king_col = king_pos
        
        # Check only opponent pieces that can attack the king
        opponent_color = 'black' if piece.color == 'white' else 'white'
        
        # Fast check: Knight attacks
        knight_moves = [
            (king_row-2, king_col+1), (king_row-1, king_col+2),
            (king_row+1, king_col+2), (king_row+2, king_col+1),
            (king_row+2, king_col-1), (king_row+1, king_col-2),
            (king_row-1, king_col-2), (king_row-2, king_col-1)
        ]
        for r, c in knight_moves:
            if Square.in_range(r, c):
                p = temp_board.squares[r][c].piece
                if isinstance(p, Knight) and p.color == opponent_color:
                    return True
        
        # Fast check: Pawn attacks
        pawn_dir = -1 if opponent_color == 'white' else 1
        for dc in [-1, 1]:
            r, c = king_row + pawn_dir, king_col + dc
            if Square.in_range(r, c):
                p = temp_board.squares[r][c].piece
                if isinstance(p, Pawn) and p.color == opponent_color:
                    return True
        
        # Fast check: King attacks (for castling validation)
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                r, c = king_row + dr, king_col + dc
                if Square.in_range(r, c):
                    p = temp_board.squares[r][c].piece
                    if isinstance(p, King) and p.color == opponent_color:
                        return True
        
        # Check sliding pieces (Queen, Rook, Bishop)
        # Diagonal directions for Bishop/Queen
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            r, c = king_row + dr, king_col + dc
            while Square.in_range(r, c):
                p = temp_board.squares[r][c].piece
                if p:
                    if p.color == opponent_color and (isinstance(p, Bishop) or isinstance(p, Queen)):
                        return True
                    break
                r += dr
                c += dc
        
        # Straight directions for Rook/Queen
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            r, c = king_row + dr, king_col + dc
            while Square.in_range(r, c):
                p = temp_board.squares[r][c].piece
                if p:
                    if p.color == opponent_color and (isinstance(p, Rook) or isinstance(p, Queen)):
                        return True
                    break
                r += dr
                c += dc
        
        return False

    def calc_moves(self, piece, row, col, bool=True):
        """OPTIMIZED: Calculate valid moves with minimal overhead"""
        piece.clear_moves()
        
        def pawn_moves():
            steps = 1 if piece.moved else 2
            start = row + piece.dir
            end = row + (piece.dir * (1 + steps))
            
            for move_row in range(start, end, piece.dir):
                if Square.in_range(move_row):
                    if self.squares[move_row][col].isempty():
                        initial = Square(row, col)
                        final = Square(move_row, col)
                        move = Move(initial, final)
                        if bool:
                            if not self.in_check(piece, move):
                                piece.add_move(move)
                        else:
                            piece.add_move(move)
                    else:
                        break
                else:
                    break

            move_row = row + piece.dir
            for move_col in [col-1, col+1]:
                if Square.in_range(move_row, move_col):
                    if self.squares[move_row][move_col].has_enemy_piece(piece.color):
                        initial = Square(row, col)
                        final_piece = self.squares[move_row][move_col].piece
                        final = Square(move_row, move_col, final_piece)
                        move = Move(initial, final)
                        if bool:
                            if not self.in_check(piece, move):
                                piece.add_move(move)
                        else:
                            piece.add_move(move)

            r = 3 if piece.color == 'white' else 4
            fr = 2 if piece.color == 'white' else 5
            for side in [-1, 1]:
                if Square.in_range(col+side) and row == r:
                    if self.squares[row][col+side].has_enemy_piece(piece.color):
                        p = self.squares[row][col+side].piece
                        if isinstance(p, Pawn) and p.en_passant:
                            initial = Square(row, col)
                            final = Square(fr, col+side, p)
                            move = Move(initial, final)
                            if bool:
                                if not self.in_check(piece, move):
                                    piece.add_move(move)
                            else:
                                piece.add_move(move)

        def knight_moves():
            possible_moves = [
                (row-2, col+1), (row-1, col+2), (row+1, col+2), (row+2, col+1),
                (row+2, col-1), (row+1, col-2), (row-1, col-2), (row-2, col-1),
            ]

            for move_row, move_col in possible_moves:
                if Square.in_range(move_row, move_col):
                    if self.squares[move_row][move_col].isempty_or_enemy(piece.color):
                        initial = Square(row, col)
                        final_piece = self.squares[move_row][move_col].piece
                        final = Square(move_row, move_col, final_piece)
                        move = Move(initial, final)
                        if bool:
                            if not self.in_check(piece, move):
                                piece.add_move(move)
                        else:
                            piece.add_move(move)

        def straightline_moves(incrs):
            for row_incr, col_incr in incrs:
                move_row = row + row_incr
                move_col = col + col_incr

                while Square.in_range(move_row, move_col):
                    initial = Square(row, col)
                    final_piece = self.squares[move_row][move_col].piece
                    final = Square(move_row, move_col, final_piece)
                    move = Move(initial, final)

                    if self.squares[move_row][move_col].isempty():
                        if bool:
                            if not self.in_check(piece, move):
                                piece.add_move(move)
                        else:
                            piece.add_move(move)
                    elif self.squares[move_row][move_col].has_enemy_piece(piece.color):
                        if bool:
                            if not self.in_check(piece, move):
                                piece.add_move(move)
                        else:
                            piece.add_move(move)
                        break
                    elif self.squares[move_row][move_col].has_team_piece(piece.color):
                        break

                    move_row += row_incr
                    move_col += col_incr

        def king_moves():
            adjs = [
                (row-1, col+0), (row-1, col+1), (row+0, col+1), (row+1, col+1),
                (row+1, col+0), (row+1, col-1), (row+0, col-1), (row-1, col-1),
            ]

            for move_row, move_col in adjs:
                if Square.in_range(move_row, move_col):
                    if self.squares[move_row][move_col].isempty_or_enemy(piece.color):
                        initial = Square(row, col)
                        final = Square(move_row, move_col)
                        move = Move(initial, final)
                        if bool:
                            if not self.in_check(piece, move):
                                piece.add_move(move)
                        else:
                            piece.add_move(move)

            if not piece.moved:
                # Queen side castling
                left_rook = self.squares[row][0].piece
                if isinstance(left_rook, Rook) and not left_rook.moved:
                    clear_path = all(not self.squares[row][c].has_piece() for c in range(1, 4))
                    if clear_path:
                        piece.left_rook = left_rook
                        moveR = Move(Square(row, 0), Square(row, 3))
                        moveK = Move(Square(row, col), Square(row, 2))
                        if bool:
                            if not self.in_check(piece, moveK) and not self.in_check(left_rook, moveR):
                                left_rook.add_move(moveR)
                                piece.add_move(moveK)
                        else:
                            left_rook.add_move(moveR)
                            piece.add_move(moveK)

                # King side castling
                right_rook = self.squares[row][7].piece
                if isinstance(right_rook, Rook) and not right_rook.moved:
                    clear_path = all(not self.squares[row][c].has_piece() for c in range(5, 7))
                    if clear_path:
                        piece.right_rook = right_rook
                        moveR = Move(Square(row, 7), Square(row, 5))
                        moveK = Move(Square(row, col), Square(row, 6))
                        if bool:
                            if not self.in_check(piece, moveK) and not self.in_check(right_rook, moveR):
                                right_rook.add_move(moveR)
                                piece.add_move(moveK)
                        else:
                            right_rook.add_move(moveR)
                            piece.add_move(moveK)

        if isinstance(piece, Pawn):
            pawn_moves()
        elif isinstance(piece, Knight):
            knight_moves()
        elif isinstance(piece, Bishop):
            straightline_moves([(-1, 1), (-1, -1), (1, 1), (1, -1)])
        elif isinstance(piece, Rook):
            straightline_moves([(-1, 0), (0, 1), (1, 0), (0, -1)])
        elif isinstance(piece, Queen):
            straightline_moves([(-1, 1), (-1, -1), (1, 1), (1, -1), (-1, 0), (0, 1), (1, 0), (0, -1)])
        elif isinstance(piece, King):
            king_moves()

    def _add_pieces(self, color):
        row_pawn, row_other = (6, 7) if color == 'white' else (1, 0)

        for col in range(COLS):
            self.squares[row_pawn][col].piece = Pawn(color)

        self.squares[row_other][1].piece = Knight(color)
        self.squares[row_other][6].piece = Knight(color)

        self.squares[row_other][2].piece = Bishop(color)
        self.squares[row_other][5].piece = Bishop(color)

        self.squares[row_other][0].piece = Rook(color)
        self.squares[row_other][7].piece = Rook(color)

        self.squares[row_other][3].piece = Queen(color)

        king = King(color)
        self.squares[row_other][4].piece = king
        self._king_positions[color] = (row_other, 4)  # Cache king position

    def to_dict(self):
        return [[square.piece.to_dict() if square.has_piece() else None 
                for square in row] 
                for row in self.squares]

    def get_all_moves(self, color):
        moves = []
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.squares[row][col].piece
                if piece and piece.color == color:
                    self.calc_moves(piece, row, col)
                    moves.extend(piece.moves)
                    piece.clear_moves()
        return moves

    def in_check_king(self, color):
        """OPTIMIZED: Use cached king position"""
        if self._king_positions[color]:
            king_row, king_col = self._king_positions[color]
        else:
            # Fallback: search for king
            king_row, king_col = None, None
            for row in range(ROWS):
                for col in range(COLS):
                    piece = self.squares[row][col].piece
                    if isinstance(piece, King) and piece.color == color:
                        king_row, king_col = row, col
                        self._king_positions[color] = (row, col)
                        break
                if king_row is not None:
                    break

        if king_row is None:
            return False

        opponent_color = 'black' if color == 'white' else 'white'
        
        # Only check pieces that can actually attack the king
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.squares[row][col].piece
                if piece and piece.color == opponent_color:
                    self.calc_moves(piece, row, col, bool=False)
                    for m in piece.moves:
                        if m.final.row == king_row and m.final.col == king_col:
                            return True
        return False

    def is_game_over(self, color):
        moves = self.get_all_moves(color)
        if not moves:
            if self.in_check_king(color):
                return 'checkmate'
            else:
                return 'stalemate'
        return False