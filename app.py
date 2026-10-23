from datetime import datetime
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from secrets import token_hex
from flask_socketio import SocketIO, join_room, emit, leave_room
from flask_migrate import Migrate
import json
import os
import re
import copy


try:
    from chess_logic import Board, Square, Move, Pawn, King, Rook
except ImportError:
    print("Warning: Could not import all classes from chess_logic.py. Assuming basic imports.")
    from chess_logic import Board, Square, Move, Pawn
    
from models import db, User, Game
from ai import ChessAI
from analysis import GameAnalyzer


app = Flask(__name__)
app.secret_key = token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chess.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

migrate = Migrate(app, db)
app.cli.add_command('db', migrate)

# Use threading for async background tasks
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    # Ensure user_id is valid integer
    try:
        return User.query.get(int(user_id))
    except (TypeError, ValueError):
        return None

# In-memory storage for active games
games = {}

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not email or not password or not confirm_password:
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        if len(username) < 3 or len(username) > 150:
            flash('Username must be between 3 and 150 characters', 'error')
            return render_template('register.html')
        
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            flash('Invalid email format', 'error')
            return render_template('register.html')
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return render_template('register.html')
        if not re.search(r'[A-Z]', password) or not re.search(r'[0-9]', password):
            flash('Password must contain at least one uppercase letter and one number', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(username=username.lower()).first():
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email.lower()).first():
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username.lower(),
            email=email.lower(),
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


# @app.route('/api/is_in_check', methods=['POST'])
# @login_required
# def api_is_in_check():
#     data = request.json
#     game_id = data.get('game_id')
#     color = data.get('color')
    
#     if game_id not in games:
#         return jsonify({'error': 'Game not found'}), 404
    
#     game = games[game_id]
#     board = game['board']
    
#     in_check = board.in_check_king(color)
    
#     return jsonify({'in_check': in_check})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username.lower()).first()
        
        if user and check_password_hash(user.password, password):
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        
        flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/analyze_game/<int:game_id>')
@login_required
def analyze_game(game_id):
    game = Game.query.get_or_404(game_id)

    if game.player_white != current_user.id and game.player_black != current_user.id:
        flash('You do not have access to this game', 'error')
        return redirect(url_for('dashboard'))

    try:
        moves_history = json.loads(game.moves) if game.moves else []
    except json.JSONDecodeError:
        moves_history = []
        flash('Could not parse move history. Analysis may be incomplete.', 'warning')

    analyzer = GameAnalyzer(moves_history)
    analysis = analyzer.analyze()

    # ---- ENSURE ALL KEYS EXIST ----
    defaults = {'blunders': 0, 'mistakes': 0, 'inaccuracies': 0, 'excellents': 0, 'avg_cp_loss': 0.0, 'good': 0,}
    for color in ['white', 'black']:
        if color not in analysis:
            analysis[color] = defaults.copy()
        else:
            for k, v in defaults.items():
                analysis[color][k] = analysis[color].get(k, v)
            analysis[color]['avg_cp_loss'] = float(analysis[color]['avg_cp_loss'])
            
            total_moves = len(moves_history)

    return render_template('analysis.html', game=game, analysis=analysis, total_moves=total_moves)
    
    


@app.route('/dashboard')
@login_required
def dashboard():
    # Refresh user stats from database
    db.session.refresh(current_user)
    
    user_games = Game.query.filter(
        (Game.player_white == current_user.id) | (Game.player_black == current_user.id)
    ).all()
    
    total_moves = 0
    for g in user_games:
        try:
            moves_data = json.loads(g.moves) if g.moves else []
            total_moves += len(moves_data)
        except Exception:
            pass # Ignore malformed move history
            
    stats = {
        'total_games': current_user.games_played,
        'wins': current_user.wins,
        'losses': current_user.losses,
        'draws': current_user.draws,
        'win_rate': current_user.get_win_rate(),
        'total_moves': total_moves,
        'avg_moves': round(total_moves / len(user_games)) if user_games else 0,
        'rating': current_user.rating,
        'last_login': current_user.last_login.strftime('%Y-%m-%d %H:%M') if hasattr(current_user, 'last_login') and current_user.last_login else 'Never'
    }
    
    recent_games = Game.query.filter(
        (Game.player_white == current_user.id) | (Game.player_black == current_user.id)
    ).order_by(Game.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html', user=current_user, stats=stats, recent_games=recent_games)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    # Refresh user stats from database
    db.session.refresh(current_user)
    
    stats = {
        'total_games': current_user.games_played,
        'wins': current_user.wins,
        'losses': current_user.losses,
        'draws': current_user.draws,
        'win_rate': current_user.get_win_rate(),
        'rating': current_user.rating,
    }

    if request.method == 'POST':
        file = request.files.get('profile_pic')
        
        if file and file.filename != '':
            allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
            
            if '.' not in file.filename:
                flash('Invalid file: no extension found.', 'error')
            else:
                ext = file.filename.rsplit('.', 1)[1].lower()
                
                if ext not in allowed:
                    flash('Only PNG, JPG, JPEG, GIF, WEBP allowed.', 'error')
                else:
                    try:
                        import time
                        timestamp = int(time.time())
                        safe_name = secure_filename(f"{current_user.id}_{timestamp}.{ext}")
                        
                        upload_folder = app.config['UPLOAD_FOLDER'].replace('\\', '/')
                        full_path = os.path.join(upload_folder, safe_name)

                        os.makedirs(upload_folder, exist_ok=True)
                        file.save(full_path)

                        if not os.path.exists(full_path):
                            flash('Upload failed: file was not saved.', 'error')
                        elif os.path.getsize(full_path) == 0:
                            os.remove(full_path)
                            flash('Upload failed: saved file is empty.', 'error')
                        elif os.path.getsize(full_path) > app.config['MAX_CONTENT_LENGTH']:
                            os.remove(full_path)
                            flash(f"File too large. Max {app.config['MAX_CONTENT_LENGTH'] // 1024 // 1024}MB.", 'error')
                        else:
                            if current_user.profile_pic and current_user.profile_pic != 'default.png':
                                old_path = os.path.join(upload_folder, current_user.profile_pic)
                                if os.path.exists(old_path):
                                    try:
                                        os.remove(old_path)
                                    except Exception as e:
                                        print(f"Could not delete old file: {e}")

                            current_user.profile_pic = safe_name
                            db.session.commit()
                            flash('Profile picture updated successfully!', 'success')
                            
                    except Exception as e:
                        print(f"Upload error: {e}")
                        flash(f'Upload error: {str(e)}', 'error')

        bio = request.form.get('bio', '').strip()
        if bio != current_user.bio:
            current_user.bio = bio
            db.session.commit()
            flash('Bio updated successfully.', 'success')

        return redirect(url_for('profile'))

    return render_template('profile.html', user=current_user, stats=stats)

@app.route('/game/<game_id>')
@login_required
def game_page(game_id):
    if game_id in games:
        session['game_id'] = game_id
        game = games[game_id]
        
        player_color = None
        if game['players']['white'] == current_user.id:
            player_color = 'white'
        elif game['players'].get('black') == current_user.id:
            player_color = 'black'
        
        return render_template('game.html', game_id=game_id, player_color=player_color, game_type=game['type'], board=game['board'].to_dict())
    else:
        flash('Game not found', 'error')
        return redirect(url_for('dashboard'))

@app.route('/start_game', methods=['POST'])
@login_required
def start_game():
    game_type = request.json.get('type')
    difficulty = request.json.get('difficulty', 3)
    
    game_id = token_hex(8)
    board = Board()
    
    games[game_id] = {
        'board': board,
        'next_player': 'white',
        'selected': None,
        'type': game_type,
        'difficulty': difficulty,
        'players': {'white': current_user.id},
        'room': game_id,
        'captured_pieces': {'white': [], 'black': []},
        'move_times': [],
        'start_time': datetime.utcnow(),
        'move_history_stack': []  # For undo functionality
    }
    
    if game_type == 'bot':
        games[game_id]['players']['black'] = 'bot'
    
    session['game_id'] = game_id
    return jsonify({
        'success': True,
        'game_id': game_id,
        'board': board.to_dict(),
        'next_player': 'white',
        'game_type': game_type
    })

@app.route('/get_game_state/<game_id>', methods=['GET'])
@login_required
def get_game_state(game_id):
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = games[game_id]
    return jsonify({
        'board': game['board'].to_dict(),
        'next_player': game['next_player'],
        'captured_pieces': game['captured_pieces'],
        'game_type': game['type'],
        'can_undo': len(game['move_history_stack']) > 0,
        'last_move': {
            'initial': {'row': game['board'].last_move.initial.row, 'col': game['board'].last_move.initial.col},
            'final': {'row': game['board'].last_move.final.row, 'col': game['board'].last_move.final.col}
        } if game['board'].last_move else None
    })

@app.route('/api/select_square', methods=['POST'])
@login_required
def api_select_square():
    data = request.json
    game_id = data.get('game_id')
    
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    row, col = data['row'], data['col']
    game = games[game_id]
    
    user_color = next((color for color, uid in game['players'].items() if uid == current_user.id), None)
    if user_color is None or game['next_player'] != user_color:
        return jsonify({'error': 'Not your turn'}), 400
    
    board = game['board']
    square = board.squares[row][col]
    
    if not (square.has_piece() and square.piece.color == game['next_player']):
        return jsonify({'valid_moves': []})
    
    piece = square.piece
    board.calc_moves(piece, row, col)
    game['selected'] = {'row': row, 'col': col, 'piece': piece}
    
    valid_moves = [{'row': m.final.row, 'col': m.final.col} for m in piece.moves]
    return jsonify({'valid_moves': valid_moves, 'selected': {'row': row, 'col': col}})

@app.route('/api/make_move', methods=['POST'])
@login_required
def api_make_move():
    """Make a move - OPTIMIZED FOR SPEED"""
    data = request.json
    game_id = data.get('game_id')
    
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = games[game_id]
    
    if not game['selected']:
        return jsonify({'error': 'No piece selected'}), 400
    
    user_color = next((color for color, uid in game['players'].items() if uid == current_user.id), None)
    if user_color is None or game['next_player'] != user_color:
        return jsonify({'error': 'Not your turn'}), 400
    
    board = game['board']
    selected = game['selected']
    piece = selected['piece']
    
    initial = Square(selected['row'], selected['col'])
    final = Square(data['row'], data['col'])
    move = Move(initial, final)
    
    if move not in piece.moves:
        return jsonify({'error': 'Invalid move'}), 400
    
    # Save state for undo (deep copy before move)
    game_state = {
        'board': copy.deepcopy(board),
        'next_player': game['next_player'],
        'captured_pieces': copy.deepcopy(game['captured_pieces'])
    }
    game['move_history_stack'].append(game_state)
    
    captured_piece = board.squares[final.row][final.col].piece
    if captured_piece:
        game['captured_pieces'][game['next_player']].append(captured_piece.to_dict())
    
    board.move(piece, move)
    
    if isinstance(piece, Pawn):
        if abs(final.row - initial.row) == 2:
            board.set_true_en_passant(piece)
    
    previous_player = game['next_player']
    game['next_player'] = 'black' if game['next_player'] == 'white' else 'white'
    game['selected'] = None
    
    response_data = {
        'success': True,
        'board': board.to_dict(),
        'next_player': game['next_player'],
        'captured_pieces': game['captured_pieces'],
        'can_undo': len(game['move_history_stack']) > 0,
        'last_move': {
            'initial': {'row': initial.row, 'col': initial.col},
            'final': {'row': final.row, 'col': final.col}
        }
    }
    
    game_over = board.is_game_over(game['next_player'])
    
    if game_over:
        winner = 'draw' if game_over == 'stalemate' else previous_player
        _save_game(game_id, winner)
        response_data['game_over'] = True
        response_data['result'] = game_over
        response_data['winner'] = winner
        return jsonify(response_data)
    
    # --- OPTIMIZED BOT MOVE ---
    if game['type'] == 'bot' and game['next_player'] == 'black' and not game_over:
        
        def process_bot_move(current_game_id):
            """Background task to calculate and make bot move - OPTIMIZED"""
            with app.app_context():
                if current_game_id not in games:
                    print(f"Bot move for {current_game_id} cancelled, game not found.")
                    return
                
                game = games[current_game_id]
                board = game['board']
                
                try:
                    ai = ChessAI(board, 'black')
                    # Reduced depth for faster response: easy=2, medium=2, hard=3
                    depth = 2 if game['difficulty'] <= 3 else 3
                    print(f"Bot calculating move at depth {depth}...")
                    
                    ai_move = ai.get_best_move(depth=depth)
                    
                    if ai_move:
                        # Save bot move state for undo
                        bot_state = {
                            'board': copy.deepcopy(board),
                            'next_player': game['next_player'],
                            'captured_pieces': copy.deepcopy(game['captured_pieces'])
                        }
                        game['move_history_stack'].append(bot_state)
                        
                        ai_piece = board.squares[ai_move.initial.row][ai_move.initial.col].piece
                        captured_by_ai = board.squares[ai_move.final.row][ai_move.final.col].piece
                        
                        if captured_by_ai:
                            game['captured_pieces']['black'].append(captured_by_ai.to_dict())
                        
                        board.move(ai_piece, ai_move)
                        game['next_player'] = 'white'
                        
                        bot_response = {
                            'board': board.to_dict(),
                            'next_player': game['next_player'],
                            'captured_pieces': game['captured_pieces'],
                            'can_undo': len(game['move_history_stack']) > 0,
                            'bot_move': {
                                'initial': {'row': ai_move.initial.row, 'col': ai_move.initial.col},
                                'final': {'row': ai_move.final.row, 'col': ai_move.final.col}
                            }
                        }
                        
                        game_over_after_bot = board.is_game_over(game['next_player'])
                        if game_over_after_bot:
                            winner = 'draw' if game_over_after_bot == 'stalemate' else 'black'
                            _save_game(current_game_id, winner)
                            bot_response['game_over'] = True
                            bot_response['result'] = game_over_after_bot
                            bot_response['winner'] = winner
                        
                        print(f"Bot move calculated: {ai_move.initial.row},{ai_move.initial.col} -> {ai_move.final.row},{ai_move.final.col}")
                        socketio.emit('bot_moved', bot_response, room=current_game_id)
                        
                except Exception as e:
                    print(f"Bot move error: {e}")
                    import traceback
                    traceback.print_exc()

        # Start background task
        socketio.start_background_task(process_bot_move, game_id)
    
    return jsonify(response_data)

@app.route('/api/undo_move', methods=['POST'])
@login_required
def api_undo_move():
    """Undo the last move(s) - FIXED VERSION"""
    data = request.json
    game_id = data.get('game_id')
    
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = games[game_id]
    
    # Check if user can undo
    user_color = next((color for color, uid in game['players'].items() if uid == current_user.id), None)
    if user_color is None:
        return jsonify({'error': 'Not authorized'}), 400
    
    if not game['move_history_stack']:
        return jsonify({'error': 'No moves to undo'}), 400
    
    # For bot games: undo both bot and player moves (if bot just moved)
    # For PvP games: undo only the last move
    
    if game['type'] == 'bot':
        # If it's white's turn, bot just moved, so undo 2 moves
        if game['next_player'] == 'white' and len(game['move_history_stack']) >= 2:
            # Pop bot's move
            game['move_history_stack'].pop()
            # Pop player's move and restore to that state
            if game['move_history_stack']:
                last_state = game['move_history_stack'][-1]
            else:
                # No moves left, reset to initial state
                game['board'] = Board()
                game['next_player'] = 'white'
                game['captured_pieces'] = {'white': [], 'black': []}
                game['selected'] = None
                
                return jsonify({
                    'success': True,
                    'board': game['board'].to_dict(),
                    'next_player': game['next_player'],
                    'captured_pieces': game['captured_pieces'],
                    'can_undo': False
                })
        elif game['next_player'] == 'black' and len(game['move_history_stack']) >= 1:
            # Player just moved, undo only player's move
            last_state = game['move_history_stack'][-1]
        else:
            return jsonify({'error': 'No moves to undo'}), 400
    else:
        # PvP: just undo the last move
        if len(game['move_history_stack']) >= 1:
            last_state = game['move_history_stack'][-1]
        else:
            return jsonify({'error': 'No moves to undo'}), 400
    
    # Restore the board state
    game['board'] = copy.deepcopy(last_state['board'])
    game['next_player'] = last_state['next_player']
    game['captured_pieces'] = copy.deepcopy(last_state['captured_pieces'])
    game['selected'] = None
    
    return jsonify({
        'success': True,
        'board': game['board'].to_dict(),
        'next_player': game['next_player'],
        'captured_pieces': game['captured_pieces'],
        'can_undo': len(game['move_history_stack']) > 0
    })

# NEW ENDPOINT: Handle resignation
@app.route('/api/resign_game', methods=['POST'])
@login_required
def api_resign_game():
    """Handle game resignation and save to database"""
    data = request.json
    game_id = data.get('game_id')
    
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = games[game_id]
    
    # Determine who resigned and who won
    user_color = next((color for color, uid in game['players'].items() if uid == current_user.id), None)
    if user_color is None:
        return jsonify({'error': 'Not authorized'}), 400
    
    # Winner is the opposite color
    winner = 'black' if user_color == 'white' else 'white'
    
    # Save the game with resignation
    _save_game(game_id, winner, resignation=True)
    
    return jsonify({
        'success': True,
        'winner': winner,
        'result': 'resignation'
    })

@socketio.on('join_game')
def on_join(data):
    game_id = data.get('game_id')
    
    if not game_id or game_id not in games:
        emit('error', {'message': 'Game not found'})
        return
    
    game = games[game_id]
    join_room(game_id)
    print(f"User {current_user.username} joined room {game_id}")
    
    if game['type'] == 'pvp' and 'black' not in game['players']:
        if game['players']['white'] != current_user.id:
            game['players']['black'] = current_user.id
            emit('player_joined', {
                'color': 'black',
                'player': current_user.username
            }, room=game_id)
            emit('game_ready', {'board': game['board'].to_dict()}, room=game_id)
    
    emit('game_state', {
        'board': game['board'].to_dict(),
        'next_player': game['next_player'],
        'captured_pieces': game['captured_pieces']
    })

@socketio.on('leave_game')
def on_leave(data):
    game_id = data.get('game_id')
    if game_id in games:
        leave_room(game_id)
        print(f"User {current_user.username} left room {game_id}")
        emit('player_left', {'player': current_user.username}, room=game_id)

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        # Fallback to UI-Avatars if file not found
        return redirect(f"https://ui-avatars.com/api/?name={filename.split('_')[0]}&size=200&background=667eea&color=fff")

def _save_game(game_id, winner, resignation=False):
    """Save game to database and update player statistics"""
    if game_id not in games:
        return
    
    game = games[game_id]
    board = game['board']
    player_black = game['players'].get('black', 'bot')
    is_bot = (player_black == 'bot')
    
    duration = int((datetime.utcnow() - game['start_time']).total_seconds())
    
    # Convert move history to JSON format - FIXED
    moves_list = []
    for move in board.moves_history:
        moves_list.append({
            'initial': {'row': move.initial.row, 'col': move.initial.col},
            'final': {'row': move.final.row, 'col': move.final.col}
        })
    
    new_game = Game(
        player_white=game['players']['white'],
        player_black=player_black if not is_bot else None,
        winner=winner,
        moves=json.dumps(moves_list),  # Save as JSON string
        is_bot_game=is_bot,
        duration=duration
    )
    
    try:
        # Update white player stats
        white_user = User.query.get(game['players']['white'])
        if white_user:
            white_user.games_played += 1
            if winner == 'draw':
                white_user.draws += 1
            elif winner == 'white':
                white_user.wins += 1
                white_user.rating += 10
            else:
                white_user.losses += 1
                white_user.rating = max(white_user.rating - 10, 0)
        
        # Update black player stats (if not bot)
        if not is_bot and player_black:
            black_user = User.query.get(player_black)
            if black_user:
                black_user.games_played += 1
                if winner == 'draw':
                    black_user.draws += 1
                elif winner == 'black':
                    black_user.wins += 1
                    black_user.rating += 10
                else:
                    black_user.losses += 1
                    black_user.rating = max(black_user.rating - 10, 0)
        
        db.session.add(new_game)
        db.session.commit()
        
        print(f"Game saved: ID={new_game.id}, Winner={winner}, Moves={len(moves_list)}, Resignation={resignation}")
        
        # Clean up game from memory
        del games[game_id]
        
    except Exception as e:
        db.session.rollback()
        print(f"Error saving game: {e}")
        import traceback
        traceback.print_exc()

@app.route('/game_history')
@login_required
def game_history():
    games_list = Game.query.filter(
        (Game.player_white == current_user.id) | (Game.player_black == current_user.id)
    ).order_by(Game.id.desc()).all()
    
    return render_template('game_history.html', games=games_list)

@app.route('/leaderboard')
def leaderboard():
    users = User.query.order_by(User.rating.desc()).limit(10).all()
    return render_template('leaderboard.html', users=users)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)