import logging
from datetime import datetime

import pyrebase
from slacker import Slacker
from slugify import slugify

from app.games.exceptions import CardExists, UnregisteredCardException
from app.games.game_player import GamePlayer
from app.games.game_session import GameSession
from app.games.listeners.console_listener import ConsoleListener
from app.games.listeners.slack_listener import SlackListener
from app.settings import (FIREBASE_API_KEY, FIREBASE_AUTH_DOMAIN, FIREBASE_AUTH_PROVIDER_X509_CERT_URL,
                          FIREBASE_AUTH_URI, FIREBASE_CLIENT_EMAIL, FIREBASE_CLIENT_ID, FIREBASE_CLIENT_X509_CERT_URL,
                          FIREBASE_DATABASE_URL, FIREBASE_PRIVATE_KEY, FIREBASE_PRIVATE_KEY_ID, FIREBASE_STORAGE_BUCKET,
                          FIREBASE_TOKEN_URI, FIREBASE_TYPE, GAME_CARD_REGISTRATION_TIMEOUT, GAME_SESSION_TIME,
                          GAME_START_TIME_BUFFER, SLACK_MESSAGES_ENABLED, SLACK_TOKEN)
from app.utils.elo_rating import calculate_new_rating

logger = logging.getLogger(__name__)


class OfficeGame:
    def __init__(self, game_name, game_version, min_max_card_count=2):
        self.core_version = '0.1.1'
        self.game_name = game_name
        self.game_version = game_version
        self.game_slug = slugify(game_name)
        self.game_listeners = []
        self.firebase = pyrebase.initialize_app({
            'apiKey': FIREBASE_API_KEY,
            'databaseURL': FIREBASE_DATABASE_URL,
            'storageBucket': FIREBASE_STORAGE_BUCKET,
            'authDomain': FIREBASE_AUTH_DOMAIN,
            'serviceAccount': {
                'type': FIREBASE_TYPE,
                'private_key_id': FIREBASE_PRIVATE_KEY_ID,
                'private_key': FIREBASE_PRIVATE_KEY.replace('\\n', '\n'),
                'client_email': FIREBASE_CLIENT_EMAIL,
                'client_id': FIREBASE_CLIENT_ID,
                'auth_uri': FIREBASE_AUTH_URI,
                'token_uri': FIREBASE_TOKEN_URI,
                'auth_provider_x509_cert_url': FIREBASE_AUTH_PROVIDER_X509_CERT_URL,
                'client_x509_cert_url': FIREBASE_CLIENT_X509_CERT_URL
            }
        })
        self.min_max_card_count = min_max_card_count
        self.current_session = GameSession(self.min_max_card_count)
        self.slack = Slacker(SLACK_TOKEN)
        self.add_game_listener(ConsoleListener(self))
        if SLACK_MESSAGES_ENABLED:
            self.add_game_listener(SlackListener(self))

        remote_current_session = self.get_current_remote_session()
        if remote_current_session is not None:
            # TODO: isoformat -> datetime for session_started?
            self.get_current_session().set_start_time(remote_current_session['session_started'])
            for simplified_player in remote_current_session['players']:
                self.get_current_session().add_player(GamePlayer.from_simplified_object(simplified_player))

        # Send a notification to listeners
        for game_listener in self.game_listeners:
            game_listener.on_startup()

    def _get_db(self):
        return self.firebase.database().child('games').child(self.game_slug)

    def _check_pending_card_registration(self, card):
        pending_registration = self.firebase.database()\
            .child('pending_registrations')\
            .child(card.get_uid()) \
            .get().val()

        if pending_registration is None:
            return False

        registration_datetime = datetime.fromtimestamp(
            int(pending_registration['timestamp'] / 1000)
        )

        if (datetime.now() - registration_datetime).total_seconds() > GAME_CARD_REGISTRATION_TIMEOUT:
            # Send a notification to listeners
            for game_listener in self.game_listeners:
                game_listener.on_pending_card_registration_timeout(pending_registration, card)
            return False

        self.register_new_game_card(card, pending_registration['user_id'])
        self.firebase.database() \
            .child('pending_registrations') \
            .child(card.get_uid()) \
            .remove()
        return True

    def _get_remote_player_information(self, card):
        existing_card = self.firebase.database().child('cards').child(card.get_uid()).get().val()

        if existing_card is None or 'slack_user_id' not in existing_card:
            raise UnregisteredCardException(card)

        # Initialize the GamePlayer object
        game_player = GamePlayer(card=card)

        # The card exists and registered to a player, grab the player from the database
        existing_player = self.firebase.database()\
            .child('players')\
            .child(existing_card['slack_user_id'])\
            .get().val()

        # The player exists in the database, add the relevant information to the GamePlayer object
        game_player.set_slack_user_id(existing_card['slack_user_id'])
        game_player.set_slack_username(existing_player['slack_username'])
        game_player.set_slack_first_name(existing_player['slack_first_name'])
        game_player.set_slack_avatar_url(existing_player['slack_avatar_url'])

        # Check if the player has statistics in the current game_slug
        existing_player_statistics = self._get_db() \
            .child('player_statistics') \
            .child(existing_card['slack_user_id']) \
            .get().val()

        if existing_player_statistics is not None:
            # The player has statistics stored in the database, add it to the GamePlayer object
            game_player.set_rating(existing_player_statistics['rating'])
            game_player.set_total_games(existing_player_statistics['total_games'])
            game_player.set_games_won(existing_player_statistics['games_lost'])
            game_player.set_games_lost(existing_player_statistics['games_won'])

        return game_player

    def get_core_version(self):
        return self.core_version

    def get_version(self):
        return self.game_version

    def get_name(self):
        return self.game_name

    def get_slug(self):
        return self.game_slug

    def add_game_listener(self, listener):
        self.game_listeners.append(listener)

    def get_current_session(self):
        return self.current_session

    # Used for administration
    def register_new_game_card(self, card, slack_user_id):
        existing_card = self.firebase.database().child('cards').child(card.get_uid()).get().val()

        if existing_card is None:
            # Card does not exist, insert the card
            self.firebase.database().child('cards').child(card.get_uid()).set({
                'slack_user_id': slack_user_id,
                'sessions': {}
            })
        else:
            # Card exists in the database
            if 'slack_user_id' not in existing_card:
                # Card exists, but is not registered to a player, update the owner (player)
                self.firebase.database().child('cards').child(card.get_uid()).update({
                    'slack_user_id': slack_user_id
                })
            elif existing_card['slack_user_id'] == slack_user_id:
                # The card is already registered to this Slack user, ignore
                logger.debug(f'Card {card} is already registered under user ID {slack_user_id}, doing nothing')
                return
            else:
                # The card exists under another player
                raise CardExists(card, existing_card['slack_user_id'])

        # Does the player exists in the database?
        existing_player = self.firebase.database().child('players').child(slack_user_id).get().val()

        if existing_player is not None:
            # Player exists in the database, just append the card to the player
            self.firebase.database()\
                .child('players')\
                .child(slack_user_id)\
                .child('cards')\
                .child(card.get_uid())\
                .set(True)

            player = GamePlayer(
                card=card,
                slack_user_id=slack_user_id,
                slack_username=existing_player['slack_username'],
                slack_first_name=existing_player['slack_first_name'],
                slack_avatar_url=existing_player['slack_avatar_url']
            )
        else:
            # Player does not exist, get the slack information of the user
            slack_user_response = self.slack.users.info(slack_user_id)
            if slack_user_response is None or not slack_user_response.successful:
                logger.error(slack_user_response.error)
                return
            slack_profile = slack_user_response.body['user']['profile']
            new_player = {
                'slack_username': slack_user_response.body['user']['name'],
                'slack_first_name': slack_profile['first_name'],
                'slack_avatar_url': slack_profile['image_512'],
                'cards': {
                    card.get_uid(): True
                }
            }

            player = GamePlayer(
                card=card,
                slack_user_id=slack_user_id,
                slack_username=new_player['slack_username'],
                slack_first_name=new_player['slack_first_name'],
                slack_avatar_url=new_player['slack_avatar_url']
            )

            # Add the new player to the database, with the card added in the card list
            self.firebase.database().child('players').child(slack_user_id).set(new_player)

            # Add the player to the player statistics of the current game_slug
            self._get_db().child('player_statistics').child(slack_user_id).set({
                'rating': 1200,
                'total_games': 0,
                'games_won': 0,
                'games_lost': 0
            })

        # Send a notification to listeners
        for game_listener in self.game_listeners:
            game_listener.on_new_card_registration(player, card)

    def start_session(self):
        self.get_current_session().start()

        # Set the start time of the current session in remote
        self._get_db().child('current_session').update({
            'session_started': self.get_current_session().start_time.isoformat()
        })

        # Send a notification to listeners
        for game_listener in self.game_listeners:
            game_listener.on_start_session(self.get_current_session().get_players())

    def end_session(self, winner_player):
        all_players = self.get_current_session().get_players().copy()

        # Remove the winner from the player list and return the first player (loser for now)
        self.get_current_session().remove_player(winner_player)
        loser_player = self.get_current_session().get_player(0)

        # Calculate the players new rating
        winner_rating = calculate_new_rating(
            player_rating=winner_player.get_rating(),
            opponent_rating=loser_player.get_rating(),
            player_won=True
        )
        loser_rating = calculate_new_rating(
            player_rating=loser_player.get_rating(),
            opponent_rating=winner_player.get_rating(),
            player_won=False
        )

        # Push the current session (which has ended) to the list of sessions in Firebase
        results = self._get_db().child('sessions').push({
            'session_started': self.get_current_session().start_time.isoformat(),
            'session_ended': datetime.now().isoformat(),
            'winner': {
                'card_uid': winner_player.get_card().get_uid(),
                'rating_before': winner_player.get_rating(),
                'rating_after': winner_rating,
                'rating_delta': winner_rating - winner_player.get_rating()
            },
            'loser': {
                'card_uid': loser_player.get_card().get_uid(),
                'rating_before': loser_player.get_rating(),
                'rating_after': loser_rating,
                'rating_delta': loser_rating - loser_player.get_rating()
            }
        })

        # Push the current session id/pk to the list of sessions for each card
        for player in all_players:
            if player.get_card().get_uid() == winner_player.get_card().get_uid():
                is_winner = True
                new_rating = winner_rating
            else:
                is_winner = False
                new_rating = loser_rating
            self.firebase.database()\
                .child('cards')\
                .child(player.get_card().get_uid())\
                .child('sessions')\
                .child(self.game_slug)\
                .child(results['name'])\
                .set({
                    'new_rating': new_rating,
                    'rating_delta': new_rating - player.get_rating(),
                    'winner': is_winner
                })

            existing_player_statistics = self._get_db()\
                .child('player_statistics')\
                .child(player.get_slack_user_id())\
                .get().val()

            # Set the player statistics
            self._get_db().child('player_statistics').child(player.get_slack_user_id()).set({
                'rating': new_rating,
                'total_games': existing_player_statistics['total_games'] + 1,
                'games_won': existing_player_statistics['games_won'] + (1 if is_winner else 0),
                'games_lost': existing_player_statistics['games_lost'] + (1 if not is_winner else 0)
            })

        # Send a notification to listeners
        for game_listener in self.game_listeners:
            game_listener.on_end_session(
                winner_player=winner_player,
                winner_new_rating=winner_rating,
                loser_player=loser_player,
                loser_new_rating=loser_rating
            )

        # Create a new session placeholder (it doesn't start until we call .start())
        self.current_session = GameSession(self.min_max_card_count)

        # Reset / remove the remote session
        self._get_db().child('current_session').remove()

    def get_seconds_left(self):
        return GAME_SESSION_TIME - self.get_current_session().get_seconds_elapsed()

    def register_card(self, card):
        if self._check_pending_card_registration(card):
            return
        try:
            reset_session = False
            player = self._get_remote_player_information(card)
            if self.get_current_session().has_all_needed_players():
                if self.get_current_session().is_session_card(card):
                    # Let's make sure we have a buffer, so that nobody wins by "accident"
                    if self.get_current_session().get_seconds_elapsed() <= GAME_START_TIME_BUFFER:
                        return
                    # We have a winner! End the session and register the winner
                    self.end_session(self.get_current_session().get_player_by_card(card))
                    return
                elif self.get_seconds_left() > 0:
                    # A new card tried to register whilst there was an active sessions
                    # Send a notification to listeners
                    for game_listener in self.game_listeners:
                        game_listener.on_existing_active_session(player)
                    return
                else:
                    # We have a new card, create a new session
                    reset_session = True
            elif self.get_current_session().should_reset():
                reset_session = True
            elif self.get_current_session().is_session_card(card) \
                    or self.get_current_session().is_session_player(player):
                # The player / card already exists in the session
                # Send a notification to listeners
                for game_listener in self.game_listeners:
                    game_listener.on_already_in_session(player, card)
                return

            if reset_session:
                # Send a notification to listeners
                for game_listener in self.game_listeners:
                    game_listener.on_session_timeout(self.get_current_session())
                self.current_session = GameSession(self.min_max_card_count)

            # Add player to the session
            self.get_current_session().add_player(player)

            # Update the current session in Firebase as well
            self._get_db().child('current_session').set({
                'players': self.get_current_session().get_players_simplified()
            })

            # Send a notification to listeners
            for game_listener in self.game_listeners:
                game_listener.on_register_player(player)

            if self.get_current_session().has_all_needed_players():
                # We have all the players/cards needed to start the game. Start the actual session
                self.start_session()
        except UnregisteredCardException:
            # Send a notification to listeners
            for game_listener in self.game_listeners:
                game_listener.on_unregistered_card_read(card)

    def get_current_remote_session(self):
        return self._get_db().child('current_session').get().val()

    def has_current_remote_session(self):
        return self.get_current_remote_session() is not None