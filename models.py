from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True) 
    password = db.Column(db.String(255), nullable=False)
    profile_pic = db.Column(db.String(255), default='default.png')
    bio = db.Column(db.Text, default='')
    games_played = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    draws = db.Column(db.Integer, default=0)
    rating = db.Column(db.Integer, default=1200, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    games_as_white = db.relationship('Game', foreign_keys='Game.player_white', backref='white_player', lazy=True)
    games_as_black = db.relationship('Game', foreign_keys='Game.player_black', backref='black_player', lazy=True)
    
    def get_win_rate(self):
        if self.games_played == 0:
            return 0
        return round((self.wins / self.games_played) * 100, 1)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Game(db.Model):
    __tablename__ = 'games'
    
    id = db.Column(db.Integer, primary_key=True)
    player_white = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    player_black = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    winner = db.Column(db.String(10), nullable=True)  # 'white', 'black', 'draw'
    moves = db.Column(db.Text, nullable=True)
    is_bot_game = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    duration = db.Column(db.Integer, default=0)
    
    def get_result(self, user_id):
        if self.winner == 'draw':
            return 'Draw'
        if (self.player_white == user_id and self.winner == 'white') or \
           (self.player_black == user_id and self.winner == 'black'):
            return 'Win'
        return 'Loss'
    
    def get_opponent_name(self, user_id):
        if self.is_bot_game:
            return 'Bot'
        if self.player_white == user_id:
            opponent = User.query.get(self.player_black)
        else:
            opponent = User.query.get(self.player_white)
        return opponent.username if opponent else 'Unknown'
    
    def __repr__(self):
        return f'<Game {self.id}>'