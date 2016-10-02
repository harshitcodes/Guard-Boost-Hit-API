"""This is the main game api for Guard Boost Hit.
Contains all the functional logic and communication(request/response)
methods used in the api."""

from __future__ import division
import endpoints
import random

from protorpc import remote, messages

from models import *
from utils import get_by_urlsafe


VALID_MOVES = ["guard", "boost", "hit"]
NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(urlsafe_game_key=messages.StringField(1),)
CANCEL_GAME_REQUEST = endpoints.ResourceContainer(urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(MakePlayForm, urlsafe_game_key=messages.StringField(1),)
GET_USER_REQUEST = endpoints.ResourceContainer(username=messages.StringField(1),)
CREATE_USER_REQUEST = endpoints.ResourceContainer(username=messages.StringField(1),
                                                  email=messages.StringField(2))


@endpoints.api(name='guard_boost_hit', version='v1')
class GuardBoostHitApi(remote.Service):
    """Main api conatining the game logic"""

    # user creation
    @endpoints.method(request_message=CREATE_USER_REQUEST,
                      response_message=UserForm,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Mehtod to create new users in the datastore"""
        if User.query(User.username == request.username).get():
            raise endpoints.ConflictException('This username is already taken.')
        user = User(username=request.username,
                    email=request.email)
        user.put()
        return user.user_form()

    # get user methods
    @endpoints.method(request_message=GET_USER_REQUEST,
                      response_message=UserForm,
                      path='get_user',
                      name='get_user',
                      http_method='GET')
    def get_user(self, request):
        """Return a User object for specified username. Requires a unique username."""
        user = User.query(User.username == request.username).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')
        return user.user_form()

    # multiple users method
    @endpoints.method(response_message=UserForms,
                      path='users',
                      name='get_users',
                      http_method='GET')
    def get_users(self, request):
        """returns all the users in the database"""
        return UserForms(users=[user.user_form() for user in User.query().order(User.username)])

    # new game method
    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """creation of a new game"""
        user = User.query(User.username == request.username).get()
        if not user:
            raise endpoints.NotFoundException('User with this username doesn;t exist!')
        game = Game.new_game(user.key)
        print "direct to the form"
        return game.to_form('Guard, get a boost and attack!!')

    # get the game
    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_form('Time to make a move!')
        else:
            raise endpoints.NotFoundException('No such game')

    # cancel game
    @endpoints.method(request_message=CANCEL_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}/quit',
                      name='quit_game',
                      http_method='PUT')
    def quit_game(self, request):
        """method to quit the game"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            if game.cancelled:
                raise endpoints.ConflictException("The game has already"
                                                  "been cancelled!")
            if game.game_over:
                raise endpoints.ConflictException("The game is already over.")
            game.cancelled = True
            game.quit_game(True)
            return game.to_form('Game Cancelled!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    # make a move
    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """makes a move and returns the game state msg"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
            raise endpoints.NotFoundException('Game not found!')
        if game.game_over:
            return game.to_form('Game already over!')

        ai_play = random.choice(VALID_MOVES)
        user_play = request.play.lower()
        if user_play not in VALID_MOVES:
            msg = 'Invalid Move Plz choose from : Boost, Guard or Hit'
            game.put()
            return game.to_form(msg)

        if user_play == ai_play:
            msg = "That's a TIE"
            game.moves.append(Move(user_play=user_play, ai_play=ai_play,
                                   result=msg))
            game.put()
            return game.to_form(msg)

        game.ai_play = user_play
        game.user_play = ai_play

        # checking the moves and conditions of winning
        if user_play == 'guard' and ai_play == 'boost' or\
           user_play == 'boost' and ai_play == 'hit' or\
           user_play == 'hit' and ai_play == 'guard':
            msg = "You Lost! The AI player's {} beats your {}".format(ai_play.title(), user_play.title())
            game.message = msg
            game.moves.append(Move(user_play=user_play, ai_play=ai_play, result=msg))
            game.put()
            game.quit_game(won=False)
            return game.to_form(msg)
        else:
            msg = """You Won, your move to {} beats mine to {}!"""\
                .format(user_play.title(), ai_play.title())
            game.message = msg
            game.moves.append(Move(user_play=user_play, ai_play=ai_play, result=msg))
            game.put()
            game.quit_game(won=True)
            return game.to_form(msg)

    # getting multiple instances of games
    @endpoints.method(response_message=GameForms,
                      path='games',
                      name='get_games',
                      http_method='GET')
    def get_games(self, request):
        """Return all games, ordered by most recent game date."""
        return GameForms(games=[game.to_form() for game in Game.query().order(-Game.match_date)])

    #  retreiving user games
    @endpoints.method(request_message=GET_USER_REQUEST,
                      response_message=GameForms,
                      path='user_games',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """returning all the games user is a part of. """
        user = User.query(User.username == request.username).get()
        if not user:
            raise endpoints.NotFoundException('A user with this username does not exist')
        # now querying for the game object
        games_query = Game.query().filter(Game.game_over == False).filter(Game.user == user.key)
        return GameForms(games=[game.to_form() for game in games_query])

    # scorelist updates of the users
    @endpoints.method(response_message=UserScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """returns all the high scores of the users in descending order"""
        all_users = User.query()
        for user in all_users:
            streak_count = 0
            max_streak_count = 0
            all_games = Game.query().filter(Game.game_over == True)\
                                    .filter(Game.cancelled == False)\
                                    .filter(Game.user == user.key).order(-Game.match_date)
            for game in all_games:
                if game.won:
                    streak_count += 1
                    if streak_count >= max_streak_count:
                        max_streak_count = streak_count
                    else:
                        streak_count = 0
            user.win_streak = max_streak_count
            user.put()
        all_users = User.query().order(-User.win_streak)  # returns the users with descending high scores
        return UserScoreForms(scores=[user.score_form() for user in all_users])

        # user standings/ranking in the game
    @endpoints.method(response_message=UserRankForms,
                      path='user_rankings',
                      name='get_user_ranking',
                      http_method='GET')
    def get_user_ranking(self, request):
        """listing the user ranks based on the win ratio of the user"""
        all_users = User.query()
        for user in all_users:
            total_games = Game.query().filter(Game.game_over == True,
                                              Game.cancelled == False,
                                              Game.user == user.key).count()
            wins = Game.query().filter(Game.game_over == True,
                                       Game.cancelled == False,
                                       Game.user == user.key,
                                       Game.won == True).count()
            win_ratio = float(wins/total_games) if total_games > 0 else 0.00
            user.wins = wins
            user.total_games = total_games
            user.win_ratio = win_ratio
            user.put()
        all_users = User.query().order(-User.win_ratio)
        return UserRankForms(rankings=[user.rank_calculator_form() for user in all_users])

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=StringMessage,
                      path='game/{urlsafe_game_key}/history',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Return a history of moves for game."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
            raise endpoints.NotFoundException('Game not found!')
        return game.to_history_form()


api = endpoints.api_server([GuardBoostHitApi])
