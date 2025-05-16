import os
import pickle
import random
import time
from datetime import datetime
import uuid

from culo_game.config.config import SUITS, VALUES, CARD_VALUES, GAME_STATE_FILE, MAX_CHAT_MESSAGES


class GameState:
    """Game state manager class"""

    _instance = None

    def __new__(cls):
        """Singleton pattern to ensure only one game state exists"""
        if cls._instance is None:
            cls._instance = super(GameState, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the game state with default values"""
        self.data = {
            'players': {},
            'table': [],
            'current_player_index': 0,
            'started': False,
            'last_card_played': None,
            'game_name': 'Culo',
            'last_action': None,
            'chat_messages': [],
            'game_over': False,
            'winner': None,
            'last_card_player_position': None,
            'last_table_length': 0,
            'required_cards_to_play': 1,
            'rankings': [],
            'current_game_players': [],
            'host_player_id': None,
            'deck_size': 1,
            'turn_start_time': None,
            'card_exchange': {
                'active': False,
                'president_id': None,
                'culo_id': None,
                'vice_president_id': None,
                'vice_culo_id': None,
                'president_cards_to_receive': [],
                'president_cards_to_give': [],
                'vice_president_card_to_receive': None,
                'vice_president_card_to_give': None,
                'president_exchange_completed': False,
                'vice_exchange_completed': False,
                'completed': False,
                'current_exchange': 'president',
                'phase': 'receive'
            }
        }

        # Try to load saved state
        self.load_state()

    def save_state(self):
        """Save the current game state to a file"""
        try:
            with open(GAME_STATE_FILE, 'wb') as f:
                pickle.dump(self.data, f)
            return True
        except Exception as e:
            print(f"Error saving game state: {e}")
            return False

    def load_state(self):
        """Load the game state from a file if it exists"""
        try:
            if os.path.exists(GAME_STATE_FILE):
                with open(GAME_STATE_FILE, 'rb') as f:
                    loaded_state = pickle.load(f)
                    self.data = loaded_state
                    self.add_system_message("🔄 Game state loaded from saved file.", "info")
                    return True
        except Exception as e:
            print(f"Error loading game state: {e}")
            # If loading fails, use the default state
        return False

    def reset(self):
        """Reset the game state to default values"""
        self._initialize()

    def add_system_message(self, message, message_type="info"):
        """Add a system message to the chat

        Args:
            message: The message text
            message_type: Type of message (info, success, warning, error)
        """
        timestamp = datetime.now().strftime('%H:%M')

        chat_message = {
            'sender': 'System',
            'text': message,
            'timestamp': timestamp,
            'id': str(uuid.uuid4()),
            'type': message_type
        }

        # Add message to chat history
        if 'chat_messages' in self.data:
            self.data['chat_messages'].append(chat_message)

            # Limit the number of stored messages
            if len(self.data['chat_messages']) > MAX_CHAT_MESSAGES:
                self.data['chat_messages'] = self.data['chat_messages'][-MAX_CHAT_MESSAGES:]

    def create_deck(self, deck_size=None):
        """Create a deck of cards

        Args:
            deck_size: The size of the deck to create (0.25, 0.5, 1, 2, 3)
                    If None, uses the game_state's deck_size

        Returns:
            A list of cards
        """
        if deck_size is None:
            deck_size = self.data['deck_size']

        # Create a standard deck
        standard_deck = []
        for suit in SUITS:
            for value in VALUES:
                standard_deck.append({'suit': suit, 'value': value, 'numeric_value': CARD_VALUES[value]})

        # Handle fractional decks
        if deck_size == 0.25:
            # 1/4 deck - one suit only
            return [card for card in standard_deck if card['suit'] == 'hearts']
        elif deck_size == 0.5:
            # 1/2 deck - two suits only
            return [card for card in standard_deck if card['suit'] in ['hearts', 'diamonds']]

        # Handle multiple decks
        final_deck = []
        num_decks = int(deck_size)
        for _ in range(num_decks):
            final_deck.extend(standard_deck.copy())

        return final_deck

    def get_player_by_position(self, position):
        """Get player data by position"""
        for player_id, player_data in self.data['players'].items():
            if player_data['position'] == position:
                return player_data
        return None

    def get_players_data(self):
        """Get formatted players data for the UI"""
        players_data = []
        for pid, data in self.data['players'].items():
            players_data.append({
                'id': pid,
                'name': data['name'],
                'position': data['position'],
                'hand_count': len(data['hand']),
                'is_current': self.data['current_player_index'] == data['position'],
                'skipped': data['skipped'],
                'rank': data.get('rank'),
                'is_host': pid == self.data['host_player_id'],
                'role': data.get('role', 'neutral')
            })

        # Sort players by position
        players_data.sort(key=lambda x: x['position'])
        return players_data
