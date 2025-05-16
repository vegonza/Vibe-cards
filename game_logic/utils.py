import uuid
from datetime import datetime

# Card suits and values
SUITS = ['hearts', 'diamonds', 'clubs', 'spades']
VALUES = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'jack', 'queen', 'king', 'ace']
# Card values for comparison (higher index = higher value)
CARD_VALUES = {'2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7, '10': 8,
               'jack': 9, 'queen': 10, 'king': 11, 'ace': 12}


def init_game_state():
    return {
        'players': {},
        'table': [],
        'current_player_index': 0,
        'started': False,
        'last_card_played': None,
        'game_name': 'Culo',
        'last_action': None,  # To track if a player skipped or played a card
        'chat_messages': [],  # Add chat messages list
        'game_over': False,   # Flag to indicate if the game is over
        'winner': None,       # Store the winner's player_id
        'last_card_player_position': None,  # Track the position of the player who played the last card
        'last_table_length': 0,  # Track the table length after last card played
        'required_cards_to_play': 1,  # Default to 1 card, can be changed to 2 or 3
        'rankings': [],  # List to track player rankings as they finish [player_id1, player_id2, ...]
        'current_game_players': [],  # Track players who started the current game
        'host_player_id': None,  # Track the host player (first to join)
        'deck_size': 1,  # Default to 1 deck, options: 0.25, 0.5, 1, 2, 3
        'turn_start_time': None,  # Track when the current turn started
        'card_exchange': {
            'active': False,  # Whether card exchange is currently active
            'president_id': None,  # ID of the president player
            'culo_id': None,  # ID of the culo player
            'vice_president_id': None,  # ID of the vice-president player
            'vice_culo_id': None,  # ID of the vice-culo player
            'president_cards_to_receive': [],  # Indices of cards selected by president to receive
            'president_cards_to_give': [],  # Indices of cards selected by president to give
            'vice_president_card_to_receive': None,  # Index of card selected by vice-president to receive
            'vice_president_card_to_give': None,  # Index of card selected by vice-president to give
            'president_exchange_completed': False,  # Whether president exchange is completed
            'vice_exchange_completed': False,  # Whether vice exchange is completed
            'completed': False,  # Whether all exchanges are completed
            'current_exchange': 'president',  # Current exchange: 'president' or 'vice'
            'phase': 'receive'  # Current phase: 'receive' or 'give'
        }
    }


def util_create_deck(game_state, deck_size=None):
    """Create a deck of cards

    Args:
        game_state: The current game state
        deck_size: The size of the deck to create (0.25, 0.5, 1, 2, 3)
                  If None, uses the game_state's deck_size

    Returns:
        A list of cards
    """
    if deck_size is None:
        deck_size = game_state['deck_size']

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


def util_add_system_message(game_state, message, message_type="info"):
    """Add a system message to the chat

    Args:
        game_state: The current game state
        message: The message text
        message_type: Type of message (info, success, warning, error)
    """
    timestamp = datetime.now().strftime('%H:%M')

    chat_message = {
        'sender': 'System',
        'text': message,
        'timestamp': timestamp,
        'id': str(uuid.uuid4()),
        'type': message_type  # Can be used for styling different types of system messages
    }

    # Handle case where game_state might not be fully initialized yet
    if 'chat_messages' in game_state:
        game_state['chat_messages'].append(chat_message)

        # Limit the number of stored messages
        max_messages = 50
        if len(game_state['chat_messages']) > max_messages:
            game_state['chat_messages'] = game_state['chat_messages'][-max_messages:]


def util_sort_cards(cards):
    """Sort cards by suit and value

    Sorts in the following order:
    1. By value (2, 3, 4, ..., Jack, Queen, King, Ace)
    2. By suit (hearts, diamonds, clubs, spades)
    """
    # Define suit order (hearts, diamonds, clubs, spades)
    suit_order = {'hearts': 0, 'diamonds': 1, 'clubs': 2, 'spades': 3}

    # Sort by numeric value first, then by suit
    return sorted(cards, key=lambda card: (card['numeric_value'], suit_order[card['suit']]))


def util_get_players_data(game_state):
    """Get formatted players data for the UI"""
    players_data = []
    for pid, data in game_state['players'].items():
        players_data.append({
            'id': pid,
            'name': data['name'],
            'position': data['position'],
            'hand_count': len(data['hand']),
            'is_current': game_state['current_player_index'] == data['position'],
            'skipped': data['skipped'],
            'rank': data.get('rank'),  # Include player rank
            'is_host': pid == game_state['host_player_id'],  # Include host status
            'role': data.get('role', 'neutral')  # Include player role
        })

    # Sort players by position
    players_data.sort(key=lambda x: x['position'])
    return players_data


def util_get_player_by_position(game_state, position):
    """Get player data by position"""
    for player_id, player_data in game_state['players'].items():
        if player_data['position'] == position:
            return player_data
    return None


def util_assign_automatic_roles(game_state, save_game_state_func=None):
    """Automatically assign roles based on player finishing order"""
    total_players = len(game_state['rankings'])
    roles_changed = False

    # Reset all roles to neutral first
    for player_id in game_state['players']:
        if game_state['players'][player_id]['role'] != 'neutral':
            game_state['players'][player_id]['role'] = 'neutral'
            roles_changed = True  # Technically, this isn't the primary trigger for saving, but good to note

    # Only assign roles if we have at least 2 players
    if total_players >= 2:
        # First player is president
        if len(game_state['rankings']) > 0:
            president_id = game_state['rankings'][0]
            if president_id in game_state['players']:  # Check if player exists
                if game_state['players'][president_id]['role'] != 'president':
                    game_state['players'][president_id]['role'] = 'president'
                    roles_changed = True
                    president_name = game_state['players'][president_id]['name']
                    util_add_system_message(game_state, f"👑 {president_name} is now the President!", "success")

        # Last player is culo
        if len(game_state['rankings']) > 0:
            culo_id = game_state['rankings'][-1]
            if culo_id in game_state['players']:  # Check if player exists
                if game_state['players'][culo_id]['role'] != 'culo':
                    game_state['players'][culo_id]['role'] = 'culo'
                    roles_changed = True
                    culo_name = game_state['players'][culo_id]['name']
                    util_add_system_message(game_state, f"💩 {culo_name} is now the Culo!", "warning")

        # If we have at least 4 players, assign vice roles
        if total_players >= 4:
            # Second player is vice-president
            if len(game_state['rankings']) > 1:
                vice_president_id = game_state['rankings'][1]
                if vice_president_id in game_state['players']:  # Check if player exists
                    if game_state['players'][vice_president_id]['role'] != 'vice-president':
                        game_state['players'][vice_president_id]['role'] = 'vice-president'
                        roles_changed = True
                        vice_president_name = game_state['players'][vice_president_id]['name']
                        util_add_system_message(
                            game_state, f"🥈 {vice_president_name} is now the Vice-President!", "success")

            # Second-to-last player is vice-culo
            if len(game_state['rankings']) > 2:  # Ensure there are enough players for this role
                vice_culo_index = total_players - 2
                if vice_culo_index < len(game_state['rankings']) and vice_culo_index >= 0:  # Check index bounds
                    vice_culo_id = game_state['rankings'][vice_culo_index]
                    if vice_culo_id in game_state['players']:  # Check if player exists
                        if game_state['players'][vice_culo_id]['role'] != 'vice-culo':
                            game_state['players'][vice_culo_id]['role'] = 'vice-culo'
                            roles_changed = True
                            vice_culo_name = game_state['players'][vice_culo_id]['name']
                            util_add_system_message(game_state, f"💩 {vice_culo_name} is now the Vice-Culo!", "warning")

        if roles_changed:
            util_add_system_message(
                game_state, f"👥 Roles have been automatically assigned based on finishing order!", "info")
            if save_game_state_func:
                save_game_state_func()
