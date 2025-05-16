import os

# Card suits and values
SUITS = ['hearts', 'diamonds', 'clubs', 'spades']
VALUES = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'jack', 'queen', 'king', 'ace']
# Card values for comparison (higher index = higher value)
CARD_VALUES = {'2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7, '10': 8,
               'jack': 9, 'queen': 10, 'king': 11, 'ace': 12}

# Turn timer settings (in seconds)
TURN_TIMER_DURATION = 15

# Define the path for saving game state
GAME_STATE_FILE = 'game_state.pickle'

# Max chat messages to store
MAX_CHAT_MESSAGES = 50


def configure_app(app):
    """Configure the Flask application"""
    app.secret_key = os.urandom(24)

    # Add any additional configuration here
    return app
