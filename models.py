# defining all the models for the database schema

import random
from datetime import date, datetime
from protorpc import messages
from google.appengine.ext import ndb
from utils import *


class User(ndb.Model):
    """User Information Attributes"""
    username = ndb.StringProperty(required=True)
    email = ndb.StringProperty(required=True)
    total_games = ndb.IntegerProperty()
    wins = ndb.IntegerProperty()
    win_streak = ndb.IntegerProperty()
    win_ratio = ndb.FloatProperty()  # for calculating the user rank

    def user_form(self):
        """Returns a user form"""
        form = UserForm()
        form.username = self.username
        form.email = self.email
        return form

    def score_form(self):
        form = UserScoreForm()
        form.username = self.username
        form.score = self.win_streak
        return form

    def rank_calculator_form(self):
        form = UserRankForm()
        form.username = self.username
        form.total_games = self.total_games
        form.wins = self.wins
        form.win_ratio = '%.4f' % self.win_ratio
        return form


class Move(ndb.Model):
    """Move object."""
    user_play = ndb.StringProperty(required=True, default='')
    ai_play = ndb.StringProperty(required=True, default='')
    result = ndb.StringProperty(required=True, default='')

    def to_dict(self):
        """Convenience method to return Move as dictionary."""
        return {'user_play': str(self.user_play), 'ai_play': str(self.ai_play),
                'result': str(self.result)}


class Game(ndb.Model):
    """Game object attributes"""
    user_play = ndb.StringProperty(required=True, default='')
    ai_play = ndb.StringProperty(required=True, default='')
    user = ndb.KeyProperty(required=True, kind='User')
    game_over = ndb.BooleanProperty(required=True, default=False)
    won = ndb.BooleanProperty(required=True, default=False)
    match_date = ndb.DateTimeProperty(required=True)
    message = ndb.StringProperty(required=True, default='')
    cancelled = ndb.BooleanProperty(required=True, default=False)
    moves = ndb.StructuredProperty(Move, repeated=True)

    @classmethod
    def new_game(cls, user):
        """method to create a new game instance"""
        game = Game(user=user,
                    match_date=datetime.today(),
                    game_over=False)
        game.put()  # saved the game in the database
        return game

    def to_form(self, message=''):
        """returns the game form """
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.username = self.user.get().username
        form.game_over = self.game_over
        form.message = message if message != '' else self.message
        form.ai_play = self.ai_play
        form.user_play = self.user_play
        form.won = self.won
        form.match_date = str(self.match_date)
        form.cancelled = self.cancelled
        for i, move in enumerate(self.moves):
            self.moves[i] = move.to_dict()
        form.moves = ', '.join(map(str, self.moves))
        return form

    def to_history_form(self):
        """ returns the log of the entire game moves in a dictionary """
        for i, move in enumerate(self.moves):
            self.moves[i] = move.to_dict()
        return StringMessage(message=', '.join(map(str, self.moves)))

    def quit_game(self, won=False):
        """ends the game"""
        self.game_over = True
        self.won = won
        self.match_date = datetime.today()
        self.put()


class GameForm(messages.Message):
    """form for game information"""
    urlsafe_key = messages.StringField(1, required=True)
    game_over = messages.BooleanField(2, required=True)
    message = messages.StringField(3, required=True)
    username = messages.StringField(4, required=True)
    ai_play = messages.StringField(5, required=True)
    user_play = messages.StringField(6, required=True)
    won = messages.BooleanField(7, required=True)
    match_date = messages.StringField(8, required=True)
    cancelled = messages.BooleanField(9, required=True, default=False)
    moves = messages.StringField(10, required=True)


class GameForms(messages.Message):
    """returns multiple game forms objects"""
    games = messages.MessageField(GameForm, 1, repeated=True)


class GameHistoryForm(messages.Message):
    """GameHistoryForm for game moves log"""
    moves = messages.StringField(1, required=True)


class NewGameForm(messages.Message):
    """creates a new game"""
    username = messages.StringField(1, required=True)


class MakePlayForm(messages.Message):
    """used to make a play in the game"""
    play = messages.StringField(1, required=True)


class UserForm(messages.Message):
    """User Form for user information"""
    username = messages.StringField(1, required=True)
    email = messages.StringField(2, required=True)


class UserForms(messages.Message):
    users = messages.MessageField(UserForm, 1, repeated=True)


class UserRankForm(messages.Message):
    username = messages.StringField(1, required=True)
    total_games = messages.IntegerField(2, required=True)
    wins = messages.IntegerField(3, required=True)
    win_ratio = messages.StringField(4, required=True)


class UserRankForms(messages.Message):
    """Return multiple objects of UserRankingForms."""
    rankings = messages.MessageField(UserRankForm, 1, repeated=True)


class UserScoreForm(messages.Message):
    """ User score info via a form"""
    username = messages.StringField(1, required=True)
    score = messages.IntegerField(2, required=True)


class UserScoreForms(messages.Message):
    """Return multiple UserScoreForms."""
    scores = messages.MessageField(UserScoreForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
