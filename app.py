import os
import random
import re
import uuid
import json
import pickle
import time
from datetime import datetime

from flask import (Flask, jsonify, redirect, render_template, request, session,
                   url_for)

app = Flask(__name__, static_folder='app/static', template_folder='app/templates')
app.secret_key = os.urandom(24)

# Define the path for saving game state
GAME_STATE_FILE = 'game_state.pickle'

# Card suits and values
SUITS = ['hearts', 'diamonds', 'clubs', 'spades']
VALUES = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'jack', 'queen', 'king', 'ace']
# Card values for comparison (higher index = higher value)
CARD_VALUES = {'2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7, '10': 8,
               'jack': 9, 'queen': 10, 'king': 11, 'ace': 12}

# Turn timer settings (in seconds)
TURN_TIMER_DURATION = 15  # 20 seconds per turn

# Initialize global game state with default values


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


# Global game state
game_state = init_game_state()


def save_game_state():
    """Save the current game state to a file"""
    try:
        with open(GAME_STATE_FILE, 'wb') as f:
            pickle.dump(game_state, f)
        return True
    except Exception as e:
        print(f"Error saving game state: {e}")
        return False


def load_game_state():
    """Load the game state from a file if it exists"""
    global game_state
    try:
        if os.path.exists(GAME_STATE_FILE):
            with open(GAME_STATE_FILE, 'rb') as f:
                loaded_state = pickle.load(f)
                game_state = loaded_state
                add_system_message("🔄 Game state loaded from saved file.", "info")
                return True
    except Exception as e:
        print(f"Error loading game state: {e}")
        # If loading fails, use the default state
        game_state = init_game_state()
    return False


# Try to load the game state at startup
load_game_state()


def create_deck(deck_size=None):
    """Create a deck of cards

    Args:
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


def add_system_message(message, message_type="info"):
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
        'type': message_type  # Can be used for styling different types of system messages
    }

    # Handle case where game_state might not be fully initialized yet
    if 'chat_messages' in game_state:
        game_state['chat_messages'].append(chat_message)

        # Limit the number of stored messages
        max_messages = 50
        if len(game_state['chat_messages']) > max_messages:
            game_state['chat_messages'] = game_state['chat_messages'][-max_messages:]


@app.route('/')
def index():
    """Show join page or redirect to game if already joined"""
    # If player is already in the game, redirect to game page
    player_id = session.get('player_id')
    if player_id and player_id in game_state['players']:
        return redirect(url_for('game'))

    # Otherwise show the join page
    return render_template('join.html')


@app.route('/join', methods=['GET', 'POST'])
def join_game():
    """Handle player joining the game"""
    error = None

    if request.method == 'POST':
        # Get player name from form
        player_name = request.form.get('player_name', '').strip()

        # Validate player name
        if not player_name:
            error = "Please enter a name."
        elif len(player_name) > 20:
            error = "Name must be 20 characters or less."
        elif not re.match(r'^[a-zA-Z0-9 _-]+$', player_name):
            error = "Name can only contain letters, numbers, spaces, underscores, and hyphens."
        else:
            # Check if game is full
            if len(game_state['players']) >= 12:
                error = "Game is full. Please wait for a spot to open."
                # Return to join page with error, no spectator mode
                return render_template('join.html', error=error)

            # Generate a unique player ID
            player_id = str(uuid.uuid4())
            session['player_id'] = player_id

            # Assign player position based on the visual order in the CSS
            # The CSS positions are arranged in this order:
            # Position 0: Bottom (90°)
            # Position 1: Right (0°)
            # Position 2: Top (270°)
            # Position 3: Left (180°)
            # Position 4: Bottom-Right (45°)
            # Position 5: Top-Right (315°)
            # Position 6: Top-Left (225°)
            # Position 7: Bottom-Left (135°)
            # etc.

            # Get existing positions
            existing_positions = [player_data['position'] for player_data in game_state['players'].values()]

            # Find the first available position
            position_order = [0, 2, 3, 1, 4, 6, 7, 5, 8, 9, 10, 11]  # Clockwise order starting from bottom
            player_position = next((pos for pos in position_order if pos not in existing_positions),
                                   len(game_state['players']))

            # Check if this is the first player (host)
            is_host = len(game_state['players']) == 0 or game_state['host_player_id'] is None
            if is_host:
                game_state['host_player_id'] = player_id

            # Initialize player in game state
            game_state['players'][player_id] = {
                'name': player_name,
                'hand': [],
                'position': player_position,
                'skipped': False,  # Track if player has skipped
                'rank': None,  # Track player's rank (gold, silver, bronze, loser)
                'is_host': is_host,  # Track if player is the host
                'role': 'neutral'  # Default role is neutral
            }

            # Add system message for player joining
            if is_host:
                add_system_message(f"👑 {player_name} has joined as the host!", "info")
            else:
                add_system_message(f"👋 {player_name} has joined the game!", "info")

            # If the game has already started, add the new player to the game
            if game_state['started']:
                # Give cards to the new player without disrupting the game
                redistribute_cards()

            # If the game hasn't started and we have at least 2 players, start it
            elif not game_state['started'] and len(game_state['players']) >= 2:
                start_game()

            # Save game state after player joins
            save_game_state()

            # Redirect to game page
            return redirect(url_for('game'))

    # Show join page with error if any
    return render_template('join.html', error=error)


def sort_cards(cards):
    """Sort cards by suit and value

    Sorts in the following order:
    1. By value (2, 3, 4, ..., Jack, Queen, King, Ace)
    2. By suit (hearts, diamonds, clubs, spades)
    """
    # Define suit order (hearts, diamonds, clubs, spades)
    suit_order = {'hearts': 0, 'diamonds': 1, 'clubs': 2, 'spades': 3}

    # Sort by numeric value first, then by suit
    return sorted(cards, key=lambda card: (card['numeric_value'], suit_order[card['suit']]))


def start_game():
    """Start the game by dealing cards to all players"""
    # Create and shuffle the deck
    deck = create_deck()
    random.shuffle(deck)

    # Count the number of players
    num_players = len(game_state['players'])

    # Calculate how many cards each player should get
    # We want to distribute the entire deck evenly
    cards_per_player = len(deck) // num_players

    # Sort players by position to ensure consistent dealing
    sorted_players = sorted(game_state['players'].items(), key=lambda x: x[1]['position'])

    # Reset rankings for new game
    game_state['rankings'] = []

    # Store current players in the game
    game_state['current_game_players'] = [player_id for player_id, _ in sorted_players]

    # Deal cards to each player
    for i, (player_id, player_data) in enumerate(sorted_players):
        # Calculate start and end indices for this player's cards
        start_idx = i * cards_per_player
        # For the last player, give them all remaining cards
        end_idx = (i + 1) * cards_per_player if i < num_players - 1 else len(deck)

        # Deal cards to this player
        player_data['hand'] = deck[start_idx:end_idx]
        # Sort the player's hand
        player_data['hand'] = sort_cards(player_data['hand'])
        # Reset skipped status
        player_data['skipped'] = False
        # Reset rank
        player_data['rank'] = None

    # Set game as started
    game_state['started'] = True

    # Define the clockwise order of positions
    position_order = [0, 2, 3, 1, 4, 6, 7, 5, 8, 9, 10, 11]

    # Get the positions of players in the game, sorted by the clockwise order
    player_positions = [player['position'] for player in game_state['players'].values()]

    # Find the first position in our order that has a player
    first_player_position = next((pos for pos in position_order if pos in player_positions), 0)

    # Set the current player to the first player in the clockwise order
    game_state['current_player_index'] = first_player_position

    game_state['table'] = []
    game_state['last_card_played'] = None
    game_state['last_action'] = None
    game_state['chat_messages'] = []  # Clear chat on new game
    game_state['turn_start_time'] = time.time()  # Initialize turn start time

    # Check if we need to initiate card exchange (president and culo roles exist)
    president_id = None
    culo_id = None
    vice_president_id = None
    vice_culo_id = None

    for player_id, player_data in game_state['players'].items():
        if player_data.get('role') == 'president':
            president_id = player_id
        elif player_data.get('role') == 'culo':
            culo_id = player_id
        elif player_data.get('role') == 'vice-president':
            vice_president_id = player_id
        elif player_data.get('role') == 'vice-culo':
            vice_culo_id = player_id

    # If both president and culo exist, initiate card exchange
    if president_id and culo_id:
        game_state['card_exchange'] = {
            'active': True,
            'president_id': president_id,
            'culo_id': culo_id,
            'vice_president_id': vice_president_id,
            'vice_culo_id': vice_culo_id,
            'president_cards_to_receive': [],
            'president_cards_to_give': [],
            'vice_president_card_to_receive': None,
            'vice_president_card_to_give': None,
            'president_exchange_completed': False,
            'vice_exchange_completed': True if not (vice_president_id and vice_culo_id) else False,
            'completed': False,
            'current_exchange': 'president',
            'phase': 'receive'
        }
        # Add system message about card exchange
        add_system_message(
            f"🔄 Card exchange is now active! President takes 2 cards from Culo and gives 2 cards back.", "info")

        if vice_president_id and vice_culo_id:
            add_system_message(
                f"🔄 Vice-President and Vice-Culo will exchange 1 card each after the President's exchange.", "info")
    else:
        # No card exchange needed
        game_state['card_exchange'] = {
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

    # Add system message for game start
    player_names = [player['name'] for player in game_state['players'].values()]
    add_system_message(f"🎮 Game started with players: {', '.join(player_names)}", "success")

    # Save game state after starting the game
    save_game_state()


def redistribute_cards():
    """Redistribute all cards when a new player joins"""
    # Get the new player (the one without cards)
    new_player_id = None
    new_player_data = None

    for player_id, player_data in game_state['players'].items():
        if len(player_data['hand']) == 0 and player_data['rank'] is None:
            new_player_id = player_id
            new_player_data = player_data
            break

    if not new_player_id:
        # No new player found, this shouldn't happen
        return

    # Create a new deck for the new player
    new_player_cards = create_deck()
    random.shuffle(new_player_cards)

    # Calculate how many cards the new player should get
    # We'll give them roughly the average number of cards other players have
    total_cards = 0
    active_players = 0

    for player_id, player_data in game_state['players'].items():
        if player_id != new_player_id and player_data['rank'] is None:
            total_cards += len(player_data['hand'])
            active_players += 1

    # If there are no other active players, give them a full deck
    if active_players == 0:
        cards_for_new_player = len(new_player_cards)
    else:
        cards_for_new_player = total_cards // active_players

    # Ensure new player gets at least some cards
    cards_for_new_player = max(cards_for_new_player, 5)

    # Give cards to the new player
    new_player_data['hand'] = new_player_cards[:cards_for_new_player]

    # Sort the new player's hand
    new_player_data['hand'] = sort_cards(new_player_data['hand'])

    # Add the new player to current game players if not already there
    if new_player_id not in game_state['current_game_players']:
        game_state['current_game_players'].append(new_player_id)

    # Add system message
    add_system_message(
        f"🃏 {new_player_data['name']} has been dealt {len(new_player_data['hand'])} cards and joined the game in progress!", "info")

    # Save game state after redistributing cards
    save_game_state()


@app.route('/game')
def game():
    """Main game page"""
    player_id = session.get('player_id')

    # If player is not in session, redirect to join page
    if not player_id:
        return redirect(url_for('index'))

    # Check if player exists in game state
    if player_id not in game_state['players']:
        # If game is full, show spectator view
        if len(game_state['players']) >= 12:
            # Game is full, but player is not in game_state. This implies an issue or direct access attempt.
            # Redirect to join, perhaps with an error or just clear session.
            session.pop('player_id', None)
            return redirect(url_for('index'))  # Or join with an error message
        else:
            # This shouldn't happen normally, but if it does, redirect to join page
            session.pop('player_id', None)  # Clear the invalid player_id
            return redirect(url_for('index'))

    # Get player data
    player_data = game_state['players'][player_id]

    # Get all players data for positioning
    players_data = get_players_data()

    # Check if it's this player's turn
    is_my_turn = game_state['current_player_index'] == player_data['position']

    # Get the top card on the table (if any)
    top_card = game_state['table'][-1] if game_state['table'] else None

    # Check if the player can play any card
    can_play = False

    # Calculate which cards are playable according to rules
    playable_cards = []
    if is_my_turn and not player_data['skipped']:
        if not top_card:  # If table is empty, player can play any card
            can_play = len(player_data['hand']) > 0
            playable_cards = list(range(len(player_data['hand'])))  # All cards are playable
        else:
            # Check for playable cards:
            # 1. Cards with equal or higher value than top card
            # 2. "2" cards (jokers) which can be played on anything
            for i, card in enumerate(player_data['hand']):
                if card['value'] == '2' or card['numeric_value'] >= top_card['numeric_value']:
                    can_play = True
                    playable_cards.append(i)

    return render_template(
        'game.html',
        player_hand=player_data['hand'],
        table=game_state['table'],
        player_name=player_data['name'],
        players=players_data,
        is_my_turn=is_my_turn,
        current_player_index=game_state['current_player_index'],
        can_play=can_play,
        playable_cards=playable_cards,  # Pass the list of playable card indices
        top_card=top_card,
        game_name=game_state['game_name'],
        last_action=game_state['last_action'],
        chat_messages=game_state['chat_messages'],  # Include chat messages
        required_cards_to_play=game_state['required_cards_to_play']  # Pass required cards count
    )


def get_players_data():
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


@app.route('/play_card', methods=['POST'])
def play_card():
    """Play one or more cards from hand to table"""
    player_id = session.get('player_id')

    if not player_id:
        return jsonify({'success': False, 'error': 'No player ID in session'})

    if player_id not in game_state['players']:
        return jsonify({'success': False, 'error': 'Player not found'})

    player_data = game_state['players'][player_id]

    if game_state['current_player_index'] != player_data['position']:
        return jsonify({'success': False, 'error': 'Not your turn'})

    if player_data['skipped']:
        return jsonify({'success': False, 'error': 'You have already skipped your turn'})

    data = request.get_json()

    # Accept either single card_index or multiple card_indices
    if 'card_index' in data:
        card_indices = [data.get('card_index')]
    else:
        card_indices = data.get('card_indices', [])

    # Get joker value if provided
    joker_value = data.get('joker_value')

    # Validate we have at least one card
    if not card_indices:
        return jsonify({'success': False, 'error': 'No cards selected'})

    # Check if number of cards matches required number
    if len(card_indices) != game_state['required_cards_to_play'] and len(game_state['table']) > 0:
        return jsonify({
            'success': False,
            'error': f'You must play exactly {game_state["required_cards_to_play"]} card(s)'
        })

    # Validate card indices are within range
    for idx in card_indices:
        if not (0 <= idx < len(player_data['hand'])):
            return jsonify({'success': False, 'error': 'Invalid card index'})

    # For multiple cards, validate they all have the same effective value
    if len(card_indices) > 1:
        reference_value = None
        is_playing_only_jokers = True
        temp_selected_cards_from_hand = [player_data['hand'][idx] for idx in card_indices]

        # Determine the reference value for the play
        for card_in_hand in temp_selected_cards_from_hand:
            if card_in_hand['value'] != '2':
                reference_value = card_in_hand['value']
                is_playing_only_jokers = False
                break

        if is_playing_only_jokers:
            if joker_value:  # All selected are jokers, and a value is specified
                reference_value = joker_value
            else:  # All selected are jokers, but no specific value given (e.g. played as '2's)
                reference_value = '2'
        elif not reference_value:  # Should only happen if card_indices was empty, but that's checked before
            return jsonify({'success': False, 'error': 'Error determining reference value for multi-card play.'})

        # Now, validate that all selected cards effectively match this reference_value
        for card_in_hand in temp_selected_cards_from_hand:
            card_original_value = card_in_hand['value']
            effective_value = card_original_value

            if card_original_value == '2':  # If the card from hand is a joker
                if joker_value:  # And a specific joker_value is provided for THIS play action
                    effective_value = joker_value
                # If no specific joker_value is provided for THIS play action,
                # but we are playing with other non-jokers (is_playing_only_jokers is False),
                # then the joker should assume the value of those non-jokers (the reference_value).
                elif not is_playing_only_jokers:
                    effective_value = reference_value
                # If only jokers are played and no joker_value is specified, they are played as '2's,
                # so effective_value remains '2', which matches reference_value '2'.

            if effective_value != reference_value:
                return jsonify({'success': False, 'error': 'Selected cards must have the same value (considering jokers).'})

    # Get the cards to be played (without removing them yet)
    selected_cards_from_hand = [player_data['hand'][idx] for idx in card_indices]

    # Determine the effective value of the play, especially if jokers are involved
    # This is for comparing against the top_card on the table.
    effective_play_value_for_comparison = None
    if joker_value:  # Player explicitly chose a value for jokers, or it was auto-set for a mixed play
        effective_play_value_for_comparison = CARD_VALUES.get(joker_value)
    elif len(selected_cards_from_hand) > 0:
        # If no explicit joker_value, but we are playing non-jokers, use their value.
        # Or if playing only jokers (as 2s), use the value of '2'.
        # The previous validation step ensured all cards in a multi-play effectively have the same value.
        first_card = selected_cards_from_hand[0]
        if first_card['value'] != '2':
            effective_play_value_for_comparison = first_card['numeric_value']
        elif not any(c['value'] != '2' for c in selected_cards_from_hand):  # All are 2s, no other cards
            effective_play_value_for_comparison = CARD_VALUES['2']  # They are played as 2s
        else:  # Mixed play (e.g. K and 2) - reference_value from previous block should be used
            # Find the non-joker card to get the reference value
            non_joker_in_selection = next((c['value'] for c in selected_cards_from_hand if c['value'] != '2'), None)
            if non_joker_in_selection:
                effective_play_value_for_comparison = CARD_VALUES.get(non_joker_in_selection)
            else:  # Should not happen if prior validation is correct
                effective_play_value_for_comparison = CARD_VALUES['2']

    # Get the top card on the table (if any)
    top_card = game_state['table'][-1] if game_state['table'] else None

    # Validate if the cards can be played according to rules
    is_valid_play = False

    # Rule 1: If table is empty, any card(s) can be played
    if not top_card:
        is_valid_play = True
        # Set the required cards to play for next player
        game_state['required_cards_to_play'] = len(selected_cards_from_hand)
    # Rule 2: "2 as Joker" rule - if all selected cards are 2s (and no specific joker_value assigned yet that makes them something else)
    # or if the determined effective_play_value_for_comparison is valid.
    elif all(card['value'] == '2' for card in selected_cards_from_hand) and not joker_value:
        is_valid_play = True  # Playing actual 2s (jokers) is always allowed if not empty
    # Rule 3: Regular rule - cards must be equal or higher value than top card
    elif effective_play_value_for_comparison is not None and effective_play_value_for_comparison >= top_card['numeric_value']:
        is_valid_play = True

    if not is_valid_play:
        # Added more descriptive error for debugging
        error_detail = f"Top card: {top_card['value'] if top_card else 'None'}. Your play (effective): {effective_play_value_for_comparison}. Joker_value provided: {joker_value}."
        return jsonify({'success': False, 'error': f'Invalid card(s). You must play card(s) with equal or higher value, or 2s. {error_detail}'})

    # Sort indices in descending order to avoid shifting issues when removing
    card_indices.sort(reverse=True)

    # Cards are valid, remove them from hand and play them
    played_cards = []
    for idx in card_indices:
        played_card = player_data['hand'].pop(idx)
        played_card['id'] = str(uuid.uuid4())  # Add card ID for tracking

        # If this is a joker and a joker value was provided, store the joker value
        if played_card['value'] == '2' and joker_value:
            # Store the original value and numeric value
            played_card['original_value'] = played_card['value']
            played_card['original_numeric_value'] = played_card['numeric_value']

            # Set the new value and numeric value
            played_card['joker_value'] = joker_value
            played_card['display_value'] = joker_value

            # Update numeric value based on joker value
            if joker_value in CARD_VALUES:
                played_card['numeric_value'] = CARD_VALUES[joker_value]

        played_cards.append(played_card)

    # Sort the remaining cards in the player's hand
    player_data['hand'] = sort_cards(player_data['hand'])

    # 1. Add cards to table
    game_state['table'].extend(played_cards)
    game_state['last_card_played'] = played_cards[-1]['id']  # For client animation
    # Track who played the last card and the table length
    game_state['last_card_player_position'] = player_data['position']
    game_state['last_table_length'] = len(game_state['table'])

    # 2. Determine previous card for matching rule
    previous_card_on_table = game_state['table'][-len(played_cards) -
                                                 1] if len(game_state['table']) > len(played_cards) else None

    # 3. Check for Win first (highest priority)
    if len(player_data['hand']) == 0:
        # Add player to rankings if not already there
        if player_id not in game_state['rankings']:
            game_state['rankings'].append(player_id)

        # Assign rank based on position in rankings
        rank_position = game_state['rankings'].index(player_id)
        total_players = len(game_state['current_game_players'])

        if rank_position == 0:
            player_data['rank'] = 'gold'
            rank_text = "🥇 Gold"
        elif rank_position == 1:
            player_data['rank'] = 'silver'
            rank_text = "🥈 Silver"
        elif rank_position == 2:
            player_data['rank'] = 'bronze'
            rank_text = "🥉 Bronze"
        else:
            player_data['rank'] = 'loser'
            rank_text = "👎 Loser"

        # Check if this was the last player to finish
        if len(game_state['rankings']) == total_players - 1:
            # Find the last player who hasn't finished
            last_player_id = None
            for remaining_id in game_state['current_game_players']:
                if remaining_id not in game_state['rankings']:
                    last_player_id = remaining_id
                    break

            if last_player_id and last_player_id in game_state['players']:
                # Assign loser rank to the last player
                game_state['rankings'].append(last_player_id)
                game_state['players'][last_player_id]['rank'] = 'loser'
                last_player_name = game_state['players'][last_player_id]['name']
                add_system_message(
                    f"👎 {last_player_name} gets the Loser rank!", "warning")

                # Only set game_over to true when all players have finished
                game_state['game_over'] = True
                add_system_message(f"🏁 Game over! All players have finished!", "success")

        # Automatically assign roles based on finishing order
        assign_automatic_roles()

        # Update the action message but don't end the game yet unless all players have finished
        game_state['last_action'] = f"{player_data['name']} has finished with {rank_text} rank!"

        # Only set winner when the game is over (all players have finished)
        if game_state['game_over']:
            game_state['winner'] = game_state['rankings'][0]  # Gold player is the winner

        # Add system message for player finishing
        add_system_message(f"🏆 {player_data['name']} has finished with {rank_text} rank!", "success")

        # Still need to process Ace power if the last card was an Ace or a joker as Ace
        last_card_value = played_cards[-1].get('joker_value', played_cards[-1]['value'])
        if last_card_value == 'ace':
            game_state['table'] = []  # Clear the table
            for p_id_loop in game_state['players']:
                game_state['players'][p_id_loop]['skipped'] = False

            # Add system message for playing an Ace
            add_system_message(
                f"🔄 {player_data['name']} played an Ace as their last card, clearing the table!", "info")
        else:
            # For non-Ace cards, advance turn as normal
            advance_to_next_player()

            # Handle skip effect if needed
            if previous_card_on_table:
                previous_value = previous_card_on_table.get('joker_value', previous_card_on_table['value'])
                current_value = played_cards[0].get('joker_value', played_cards[0]['value'])

                if previous_value == current_value:
                    # Add system message for skip effect
                    next_player = get_player_by_position(game_state['current_player_index'])
                    if next_player:
                        add_system_message(
                            f"⏭️ {next_player['name']} is skipped due to matching card values!", "warning")
                    advance_to_next_player()

        # Save game state after a player finishes
        save_game_state()

        return jsonify({'success': True, 'refresh': True})

    # 4. Handle Ace Power (second priority) - either real Ace or joker as Ace
    last_card_value = played_cards[-1].get('joker_value', played_cards[-1]['value'])
    if last_card_value == 'ace':
        game_state['table'] = []  # Clear the table

        # Different message depending on if it was a real ace or a joker
        if played_cards[-1]['value'] == '2':
            game_state['last_action'] = f"{player_data['name']} played a Joker as Ace, cleared the table, and plays again!"
            add_system_message(
                f"🔄 {player_data['name']} played a Joker as Ace, clearing the table and getting another turn!", "info")
        else:
            game_state['last_action'] = f"{player_data['name']} played an Ace, cleared the table, and plays again!"
            add_system_message(
                f"🔄 {player_data['name']} played an Ace, clearing the table and getting another turn!", "info")

        for p_id_loop in game_state['players']:  # Reset skipped status for all
            game_state['players'][p_id_loop]['skipped'] = False

        # Reset to 1 card after an Ace clears the table
        game_state['required_cards_to_play'] = 1
        game_state['turn_start_time'] = time.time()  # Reset timer for the current player's new turn

        # Save game state after an Ace play
        save_game_state()

        return jsonify({'success': True, 'refresh': True})

    # 5. Determine base action message (if not an Ace)
    card_value = played_cards[0].get('joker_value', played_cards[0]['value'])  # All cards have same value
    card_suit = played_cards[0]['suit']
    is_joker = played_cards[0]['value'] == '2'

    if is_joker:
        if len(played_cards) > 1:
            base_action_message = f"{player_data['name']} played {len(played_cards)} Jokers as {card_value}s"
            add_system_message(f"🃏 {player_data['name']} played {len(played_cards)} Jokers as {card_value}s!", "info")
        else:
            base_action_message = f"{player_data['name']} played a Joker as {card_value} of {card_suit}"
            add_system_message(f"🃏 {player_data['name']} played a Joker as {card_value} of {card_suit}!", "info")
    else:
        if len(played_cards) > 1:
            base_action_message = f"{player_data['name']} played {len(played_cards)} {card_value}s"
            add_system_message(
                f"🎮 {player_data['name']} played {len(played_cards)} {card_value}s", "info")
        else:
            base_action_message = f"{player_data['name']} played {card_value} of {card_suit}"
            if card_value in ['jack', 'queen', 'king', '10']:
                add_system_message(
                    f"🎮 {player_data['name']} played {card_value} of {card_suit}", "info")

    current_action_message = base_action_message

    # 6. Check for "same card value" skip effect
    skip_triggered_by_match = False
    if previous_card_on_table:
        previous_value = previous_card_on_table.get('joker_value', previous_card_on_table['value'])

        if previous_value == card_value:
            current_action_message += f". This matches the previous card ({previous_value}), so the next player is skipped!"
            skip_triggered_by_match = True

    if not skip_triggered_by_match:
        # No match, or no previous card. Finalize the default message.
        if is_joker:
            current_action_message += "!"  # Add exclamation for joker if no skip
        else:
            current_action_message += "."  # Add period for regular play if no skip

    game_state['last_action'] = current_action_message

    # 7. Advance turn
    advance_to_next_player()

    # 8. If skip was triggered by match, advance again
    if skip_triggered_by_match:
        # Get the player who is being skipped
        skipped_player = get_player_by_position(game_state['current_player_index'])
        if skipped_player:
            add_system_message(f"⏭️ {skipped_player['name']} is skipped due to matching card values!", "warning")
        advance_to_next_player()

    # Save game state after playing cards
    save_game_state()

    return jsonify({
        'success': True,
        'refresh': True,
        'required_cards_to_play': game_state['required_cards_to_play']
    })


@app.route('/skip_turn', methods=['POST'])
def skip_turn():
    """Skip the current player's turn"""
    player_id = session.get('player_id')

    if not player_id:
        return jsonify({'success': False, 'error': 'No player ID in session'})

    # Check if player exists and it's their turn
    if player_id not in game_state['players']:
        return jsonify({'success': False, 'error': 'Player not found'})

    player_data = game_state['players'][player_id]

    # Check if it's this player's turn
    if game_state['current_player_index'] != player_data['position']:
        return jsonify({'success': False, 'error': 'Not your turn'})

    # Check if player has already skipped
    if player_data['skipped']:
        return jsonify({'success': False, 'error': 'You have already skipped your turn'})

    # Mark player as skipped
    player_data['skipped'] = True

    # Record the action
    game_state['last_action'] = f"{player_data['name']} skipped their turn"

    # Add system message for skipping turn
    add_system_message(f"⏩ {player_data['name']} skipped their turn", "warning")

    # Check if all active players (without ranks) have now skipped
    all_active_skipped = True
    for pid, player in game_state['players'].items():
        # If any player without a rank hasn't skipped, not all have skipped
        if player['rank'] is None and not player['skipped']:
            all_active_skipped = False
            break

    # If all active players have skipped, clear the table
    if all_active_skipped:
        game_state['table'] = []
        game_state['last_action'] = "All active players skipped. Table cleared!"
        add_system_message("🔄 All active players skipped! Table has been cleared for a new round.", "info")

        # Reset all active players' skipped status
        for player in game_state['players'].values():
            if player['rank'] is None:
                player['skipped'] = False

        # Reset last_card_player_position and last_table_length since table is now empty
        game_state['last_card_player_position'] = None
        game_state['last_table_length'] = 0

    # Move to next player
    advance_to_next_player()

    # Save game state after skipping turn
    save_game_state()

    return jsonify({
        'success': True,
        'refresh': True,  # Signal to refresh the game state
        'required_cards_to_play': game_state['required_cards_to_play']  # Include required cards count
    })


def advance_to_next_player():
    """Move to the next player in turn order"""
    num_players = len(game_state['players'])

    previous_player_index = game_state['current_player_index']
    previous_table_length = len(game_state['table'])

    # Define the clockwise order of positions
    position_order = [0, 2, 3, 1, 4, 6, 7, 5, 8, 9, 10, 11]

    # Get active positions (positions of players in the game) in the correct clockwise order
    player_current_positions = {player['position'] for player in game_state['players'].values()}
    active_positions = [pos for pos in position_order if pos in player_current_positions]

    # Find the current position's index in our active positions list
    try:
        current_position_idx = active_positions.index(game_state['current_player_index'])
    except ValueError:
        # If current position is not found (shouldn't happen), default to the first position
        current_position_idx = 0
        if active_positions:
            game_state['current_player_index'] = active_positions[0]

    # Find the next player who hasn't skipped and hasn't finished (no rank)
    for _ in range(num_players * 2):  # Increased loop limit to ensure we find a valid player
        # Move to next player in the clockwise order
        current_position_idx = (current_position_idx + 1) % len(active_positions)
        game_state['current_player_index'] = active_positions[current_position_idx]

        # Get the current player
        current_player = None
        for player in game_state['players'].values():
            if player['position'] == game_state['current_player_index']:
                current_player = player
                break

        # If no player found at this position (shouldn't happen), continue to next position
        if not current_player:
            continue

        # If this player hasn't skipped and hasn't finished (no rank), break the loop
        if not current_player['skipped'] and current_player['rank'] is None:
            break

        # If we've checked all players and all remaining players have ranks or have skipped,
        # we need to handle this special case
        if _ >= num_players - 1:
            # Check if all remaining players (those without ranks) have skipped
            all_active_skipped = True
            for player in game_state['players'].values():
                if player['rank'] is None and not player['skipped']:
                    all_active_skipped = False
                    break

            # If all active players skipped, reset skip status for all players without ranks
            if all_active_skipped:
                for player in game_state['players'].values():
                    if player['rank'] is None:
                        player['skipped'] = False

                # Try again with reset skip statuses (will be handled in the next iteration)
                continue

    # Reset turn timer for the new player
    game_state['turn_start_time'] = time.time()

    # --- NEW RULE: If round returns to last card player and no new card was played ---
    # Only if table is not empty (otherwise, it's already a new round)
    if (
        game_state['table'] and
        game_state.get('last_card_player_position') is not None and
        game_state['current_player_index'] == game_state.get('last_card_player_position') and
        len(game_state['table']) == game_state.get('last_table_length', 0)
    ):
        # Clear the table and let this player start
        game_state['table'] = []
        game_state['last_action'] = "Round returned to the player who placed the last card. Table cleared! Same player starts."
        add_system_message(
            "🔄 No one played after the last card. Table cleared and the same player starts the new round!", "info")
        # Reset all players' skipped status
        for player in game_state['players'].values():
            if player['rank'] is None:  # Only reset skip status for players still in the game
                player['skipped'] = False
        # Reset last_card_player_position and last_table_length since table is now empty
        game_state['last_card_player_position'] = None
        game_state['last_table_length'] = 0

        # Save game state after clearing table
        save_game_state()
        return  # End turn advancement here

    # If all active players (those without ranks) have skipped, reset the table and skipped status
    all_active_skipped = True
    for player in game_state['players'].values():
        if player['rank'] is None and not player['skipped']:
            all_active_skipped = False
            break

    if all_active_skipped:
        game_state['table'] = []
        game_state['last_action'] = "All active players skipped. Table cleared!"

        # Add system message for all players skipping
        add_system_message("🔄 All active players skipped! Table has been cleared for a new round.", "info")

        # Reset all active players' skipped status
        for player in game_state['players'].values():
            if player['rank'] is None:  # Only reset skip status for players still in the game
                player['skipped'] = False
        # Reset last_card_player_position and last_table_length since table is now empty
        game_state['last_card_player_position'] = None
        game_state['last_table_length'] = 0

        # Save game state after clearing table due to all players skipping
        save_game_state()


@app.route('/reset_game', methods=['POST'])
def reset_game():
    """Reset the game state"""
    player_id = session.get('player_id')

    # Check if player is the host
    if player_id != game_state['host_player_id']:
        return jsonify({
            'success': False,
            'error': 'Only the host can reset the game'
        })

    # Clear the table and player hands
    game_state['table'] = []
    game_state['game_over'] = False
    game_state['winner'] = None
    game_state['required_cards_to_play'] = 1  # Reset to 1 card per play
    game_state['rankings'] = []  # Reset rankings

    # Reset card exchange state
    game_state['card_exchange'] = {
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

    for player_id, player_data in game_state['players'].items():
        player_data['hand'] = []
        player_data['skipped'] = False
        player_data['rank'] = None  # Reset rank
        # Don't reset roles - roles persist across games unless manually changed

    # Start a new game
    start_game()

    game_state['last_action'] = "Game has been reset by the host"

    # Add system message for game reset
    host_name = game_state['players'][game_state['host_player_id']]['name']
    add_system_message(f"🔄 {host_name} (host) has reset the game! Starting a new game...", "info")

    # Keep chat history but add a divider
    add_system_message("------------------------", "divider")

    # Save game state after reset
    save_game_state()

    return jsonify({
        'success': True,
        'refresh': True  # Signal to refresh the game state
    })


@app.route('/get_game_state')
def get_game_state():
    """Get the current game state for the player"""
    player_id = session.get('player_id')

    if not player_id:
        return jsonify({'success': False, 'error': 'No player ID in session'})

    if player_id not in game_state['players']:
        return jsonify({'success': False, 'error': 'Player not found'})

    player_data = game_state['players'][player_id]

    # Get all players data for positioning
    players_data = get_players_data()

    # Check if it's this player's turn
    is_my_turn = game_state['current_player_index'] == player_data['position']

    # Check if player is host
    is_host = player_id == game_state['host_player_id']

    # Get the top card on the table (if any)
    top_card = game_state['table'][-1] if game_state['table'] else None

    # Check if the player can play any card and which cards are playable
    can_play = False
    playable_cards = []

    # If card exchange is active, don't allow playing cards
    if game_state['card_exchange']['active'] and not game_state['card_exchange']['completed']:
        can_play = False
        playable_cards = []
    elif is_my_turn and not player_data['skipped']:
        if not top_card:  # If table is empty, player can play any card
            can_play = len(player_data['hand']) > 0
            playable_cards = list(range(len(player_data['hand'])))  # All cards are playable
        else:
            # Check for playable cards:
            # 1. Cards with equal or higher value than top card
            # 2. "2" cards (jokers) which can be played on anything
            for i, card in enumerate(player_data['hand']):
                if card['value'] == '2' or card['numeric_value'] >= top_card['numeric_value']:
                    can_play = True
                    playable_cards.append(i)

    # Get rankings information
    rankings_info = []
    for rank_idx, p_id in enumerate(game_state['rankings']):
        if p_id in game_state['players']:
            player = game_state['players'][p_id]
            rank_name = ''
            if rank_idx == 0:
                rank_name = 'gold'
            elif rank_idx == 1:
                rank_name = 'silver'
            elif rank_idx == 2:
                rank_name = 'bronze'
            else:
                rank_name = 'loser'

            rankings_info.append({
                'player_id': p_id,
                'player_name': player['name'],
                'rank': rank_name,
                'position': rank_idx + 1
            })

    # Card exchange information
    card_exchange_info = None
    if game_state['card_exchange']['active']:
        # Get hands for exchange based on current exchange type and phase
        exchange_hands = {}

        # For president exchange
        if game_state['card_exchange']['current_exchange'] == 'president':
            if player_id == game_state['card_exchange']['president_id'] and game_state['card_exchange']['phase'] == 'receive':
                culo_id = game_state['card_exchange']['culo_id']
                if culo_id in game_state['players']:
                    exchange_hands['culo_hand'] = sort_cards(game_state['players'][culo_id]['hand'])

        # For vice exchange
        elif game_state['card_exchange']['current_exchange'] == 'vice':
            if player_id == game_state['card_exchange']['vice_president_id'] and game_state['card_exchange']['phase'] == 'receive':
                vice_culo_id = game_state['card_exchange']['vice_culo_id']
                if vice_culo_id in game_state['players']:
                    exchange_hands['vice_culo_hand'] = sort_cards(game_state['players'][vice_culo_id]['hand'])

        card_exchange_info = {
            'active': True,
            'is_president': player_id == game_state['card_exchange']['president_id'],
            'is_culo': player_id == game_state['card_exchange']['culo_id'],
            'is_vice_president': player_id == game_state['card_exchange']['vice_president_id'],
            'is_vice_culo': player_id == game_state['card_exchange']['vice_culo_id'],
            'president_cards_to_receive': game_state['card_exchange']['president_cards_to_receive'],
            'president_cards_to_give': game_state['card_exchange']['president_cards_to_give'],
            'vice_president_card_to_receive': game_state['card_exchange']['vice_president_card_to_receive'],
            'vice_president_card_to_give': game_state['card_exchange']['vice_president_card_to_give'],
            'president_exchange_completed': game_state['card_exchange']['president_exchange_completed'],
            'vice_exchange_completed': game_state['card_exchange']['vice_exchange_completed'],
            'completed': game_state['card_exchange']['completed'],
            'current_exchange': game_state['card_exchange']['current_exchange'],
            'phase': game_state['card_exchange']['phase'],
            **exchange_hands
        }

    # Calculate turn timer information
    turn_timer_info = None
    # Timer should run if turn_start_time is set, game is not over,
    # AND (card exchange is not active OR it is active and completed)
    if game_state['turn_start_time'] is not None and \
       not game_state['game_over'] and \
       (not game_state['card_exchange']['active'] or game_state['card_exchange']['completed']):

        elapsed_time = time.time() - game_state['turn_start_time']
        time_left = max(0, TURN_TIMER_DURATION - elapsed_time)
        turn_timer_info = {
            'duration': TURN_TIMER_DURATION,
            'time_left': time_left,
            'percentage': (time_left / TURN_TIMER_DURATION) * 100 if TURN_TIMER_DURATION > 0 else 0
        }

        # Auto-skip logic:
        # Identify the actual current player based on game_state['current_player_index']
        actual_current_player_data_for_skip = None
        for p_data_loop in game_state['players'].values():  # Iterate through player data directly
            if p_data_loop['position'] == game_state['current_player_index']:
                actual_current_player_data_for_skip = p_data_loop
                break

        # Check if the identified current player timed out
        if actual_current_player_data_for_skip and time_left <= 0:
            # Ensure this player hasn't already been skipped (e.g. by another concurrent request)
            # and is still in play (not ranked)
            if not actual_current_player_data_for_skip['skipped'] and actual_current_player_data_for_skip['rank'] is None:
                actual_current_player_data_for_skip['skipped'] = True
                game_state['last_action'] = f"{actual_current_player_data_for_skip['name']} ran out of time and skipped their turn"
                add_system_message(
                    f"⏱️ {actual_current_player_data_for_skip['name']} ran out of time and skipped their turn", "warning")

                # After this player is skipped due to timeout, check if all active players are now skipped
                all_remaining_active_players_skipped = True
                num_active_players_for_skip_check = 0
                for p_check_data in game_state['players'].values():
                    if p_check_data['rank'] is None:  # Player is active
                        num_active_players_for_skip_check += 1
                        if not p_check_data['skipped']:  # Found an active player who is not skipped
                            all_remaining_active_players_skipped = False
                            break

                if all_remaining_active_players_skipped and num_active_players_for_skip_check > 0:
                    game_state['table'] = []
                    game_state['last_action'] = "All active players now skipped (timeout). Table cleared!"
                    add_system_message("🔄 All active players now skipped (due to timeout)! Table cleared.", "info")
                    # Reset skipped status for all active players for the new round
                    for p_reset_data in game_state['players'].values():
                        if p_reset_data['rank'] is None:
                            p_reset_data['skipped'] = False
                    game_state['last_card_player_position'] = None
                    game_state['last_table_length'] = 0
                    game_state['required_cards_to_play'] = 1  # Reset to 1 for new round
                    # Current player (who timed out) will be advanced by advance_to_next_player()

                advance_to_next_player()
                save_game_state()
                # The player_data for the *requesting* client will be fetched below based on the updated game_state.

    # Player data for the specific client making the request.
    # This needs to be fetched *after* any potential auto-skip modification to game_state.
    player_data = game_state['players'][player_id]
    # Re-calculate is_my_turn after potential changes from auto-skip
    is_my_turn = game_state['current_player_index'] == player_data['position']
    # Re-calculate players_data after potential changes
    players_data = get_players_data()
    # Re-calculate can_play and playable_cards based on potentially updated state
    can_play = False
    playable_cards = []
    if not game_state['card_exchange']['active'] or game_state['card_exchange']['completed']:
        if is_my_turn and not player_data['skipped'] and player_data['rank'] is None:  # Check rank here too
            top_card = game_state['table'][-1] if game_state['table'] else None
            if not top_card:
                can_play = len(player_data['hand']) > 0
                playable_cards = list(range(len(player_data['hand'])))
            else:
                for i, card in enumerate(player_data['hand']):
                    if card['value'] == '2' or card['numeric_value'] >= top_card['numeric_value']:
                        can_play = True
                        playable_cards.append(i)

    sorted_hand = sort_cards(player_data['hand'])

    return jsonify({
        'success': True,
        'my_name': player_data['name'],
        'player_hand': sorted_hand,  # Send the sorted hand
        'table': game_state['table'],
        'players': players_data,
        'is_my_turn': is_my_turn,
        'is_host': is_host,  # Include host status
        'can_play': can_play,
        'playable_cards': playable_cards,  # Include the list of playable card indices
        'current_player_index': game_state['current_player_index'],
        'last_card_played': game_state['last_card_played'],
        'game_name': game_state['game_name'],
        'last_action': game_state['last_action'],
        'chat_messages': game_state['chat_messages'],  # Include chat messages
        'game_over': game_state['game_over'],  # Include game over status
        'winner': game_state['winner'],  # Include winner ID
        'required_cards_to_play': game_state['required_cards_to_play'],  # Include required cards count
        'rankings': rankings_info,  # Include rankings information
        'deck_size': game_state['deck_size'],  # Include deck size
        'card_exchange': card_exchange_info,  # Include card exchange information
        'turn_timer': turn_timer_info  # Include turn timer information
    })


@app.route('/send_message', methods=['POST'])
def send_message():
    """Handle sending chat messages"""
    player_id = session.get('player_id')
    if not player_id or player_id not in game_state['players']:
        return jsonify({'success': False, 'error': 'Player not found or not in session'})

    player_name = game_state['players'][player_id]['name']
    data = request.get_json()
    message_text = data.get('message', '').strip()

    if not message_text:
        return jsonify({'success': False, 'error': 'Message cannot be empty'})

    if len(message_text) > 200:  # Limit message length
        return jsonify({'success': False, 'error': 'Message too long (max 200 chars)'})

    timestamp = datetime.now().strftime('%H:%M')

    chat_message = {
        'sender': player_name,
        'text': message_text,
        'timestamp': timestamp,
        'id': str(uuid.uuid4())  # Unique ID for each message
    }

    game_state['chat_messages'].append(chat_message)

    # Limit the number of stored messages
    max_messages = 50
    if len(game_state['chat_messages']) > max_messages:
        game_state['chat_messages'] = game_state['chat_messages'][-max_messages:]

    # Save game state after sending a message
    # Only save every 5th message to reduce disk I/O
    if len(game_state['chat_messages']) % 5 == 0:
        save_game_state()

    return jsonify({'success': True})


def get_player_by_position(position):
    """Get player data by position"""
    for player_id, player_data in game_state['players'].items():
        if player_data['position'] == position:
            return player_data
    return None


@app.route('/assign_roles', methods=['POST'])
def assign_roles():
    """Assign roles to players (host only)"""
    player_id = session.get('player_id')

    # Check if player is the host
    if player_id != game_state['host_player_id']:
        return jsonify({
            'success': False,
            'error': 'Only the host can assign roles'
        })

    data = request.get_json()
    roles = data.get('roles', [])

    if not roles:
        return jsonify({
            'success': False,
            'error': 'No roles provided'
        })

    # Update player roles
    for role_data in roles:
        target_player_id = role_data.get('player_id')
        role = role_data.get('role')

        if target_player_id in game_state['players'] and role in ['neutral', 'president', 'vice-president', 'vice-culo', 'culo']:
            game_state['players'][target_player_id]['role'] = role

    # Add system message
    host_name = game_state['players'][game_state['host_player_id']]['name']
    add_system_message(f"👑 {host_name} (host) has assigned player roles!", "info")

    # Save game state after role assignment
    save_game_state()

    return jsonify({
        'success': True
    })


@app.route('/assign_ranks', methods=['POST'])
def assign_ranks():
    """Assign ranks to players (host only)"""
    player_id = session.get('player_id')

    # Check if player is the host
    if player_id != game_state['host_player_id']:
        return jsonify({
            'success': False,
            'error': 'Only the host can assign ranks'
        })

    data = request.get_json()
    ranks = data.get('ranks', [])

    if not ranks:
        return jsonify({
            'success': False,
            'error': 'No ranks provided'
        })

    # Update player ranks
    for rank_data in ranks:
        target_player_id = rank_data.get('player_id')
        rank = rank_data.get('rank')

        if target_player_id in game_state['players'] and rank in ['gold', 'silver', 'bronze', 'loser', None]:
            game_state['players'][target_player_id]['rank'] = rank

            # Add to rankings list if not already there
            if rank and target_player_id not in game_state['rankings']:
                game_state['rankings'].append(target_player_id)
            # Remove from rankings if rank is None
            elif not rank and target_player_id in game_state['rankings']:
                game_state['rankings'].remove(target_player_id)

    # Add system message
    host_name = game_state['players'][game_state['host_player_id']]['name']
    add_system_message(f"👑 {host_name} (host) has manually assigned player ranks!", "info")

    # Save game state after rank assignment
    save_game_state()

    return jsonify({
        'success': True
    })


def assign_automatic_roles():
    """Automatically assign roles based on player finishing order"""
    total_players = len(game_state['rankings'])

    # Reset all roles to neutral first
    for player_id in game_state['players']:
        game_state['players'][player_id]['role'] = 'neutral'

    # Only assign roles if we have at least 2 players
    if total_players >= 2:
        # First player is president
        if len(game_state['rankings']) > 0:
            president_id = game_state['rankings'][0]
            game_state['players'][president_id]['role'] = 'president'
            president_name = game_state['players'][president_id]['name']
            add_system_message(f"👑 {president_name} is now the President!", "success")

        # Last player is culo
        if len(game_state['rankings']) > 0:
            culo_id = game_state['rankings'][-1]
            game_state['players'][culo_id]['role'] = 'culo'
            culo_name = game_state['players'][culo_id]['name']
            add_system_message(f"💩 {culo_name} is now the Culo!", "warning")

        # If we have at least 4 players, assign vice roles
        if total_players >= 4:
            # Second player is vice-president
            if len(game_state['rankings']) > 1:
                vice_president_id = game_state['rankings'][1]
                game_state['players'][vice_president_id]['role'] = 'vice-president'
                vice_president_name = game_state['players'][vice_president_id]['name']
                add_system_message(f"🥈 {vice_president_name} is now the Vice-President!", "success")

            # Second-to-last player is vice-culo
            if len(game_state['rankings']) > 2:
                vice_culo_index = total_players - 2
                if vice_culo_index < len(game_state['rankings']):
                    vice_culo_id = game_state['rankings'][vice_culo_index]
                    game_state['players'][vice_culo_id]['role'] = 'vice-culo'
                    vice_culo_name = game_state['players'][vice_culo_id]['name']
                    add_system_message(f"💩 {vice_culo_name} is now the Vice-Culo!", "warning")

        # Add system message about role assignment
        add_system_message(f"👥 Roles have been automatically assigned based on finishing order!", "info")

        # Save game state after roles are automatically assigned
        save_game_state()


@app.route('/change_deck_size', methods=['POST'])
def change_deck_size():
    """Change the deck size (host only)"""
    player_id = session.get('player_id')

    # Check if player is the host
    if player_id != game_state['host_player_id']:
        return jsonify({
            'success': False,
            'error': 'Only the host can change the deck size'
        })

    data = request.get_json()
    new_deck_size = data.get('deck_size')

    # Validate deck size
    valid_deck_sizes = [0.25, 0.5, 1, 2, 3]
    if new_deck_size not in valid_deck_sizes:
        return jsonify({
            'success': False,
            'error': 'Invalid deck size. Valid options are 0.25, 0.5, 1, 2, 3'
        })

    # Update deck size
    game_state['deck_size'] = new_deck_size

    # Add system message
    host_name = game_state['players'][game_state['host_player_id']]['name']
    deck_size_text = "1/4" if new_deck_size == 0.25 else "1/2" if new_deck_size == 0.5 else str(int(new_deck_size))
    add_system_message(f"🃏 {host_name} changed the deck size to {deck_size_text} deck(s)!", "info")

    # Save game state after changing deck size
    save_game_state()

    return jsonify({
        'success': True
    })


@app.route('/exchange_card', methods=['POST'])
def exchange_card():
    """Handle card exchange between players with roles"""
    player_id = session.get('player_id')

    if not player_id:
        return jsonify({'success': False, 'error': 'No player ID in session'})

    if player_id not in game_state['players']:
        return jsonify({'success': False, 'error': 'Player not found'})

    # Check if card exchange is active
    if not game_state['card_exchange']['active'] or game_state['card_exchange']['completed']:
        return jsonify({'success': False, 'error': 'Card exchange is not active'})

    # Get request data
    data = request.get_json()
    card_index = data.get('card_index')
    phase = data.get('phase')  # 'receive' or 'give'
    exchange_type = data.get('exchange_type', game_state['card_exchange']['current_exchange'])  # 'president' or 'vice'

    if card_index is None:
        return jsonify({'success': False, 'error': 'No card index provided'})

    # Determine which exchange we're handling
    if exchange_type == 'president':
        # President-Culo exchange (2 cards each)
        # Check if player is president
        is_president = player_id == game_state['card_exchange']['president_id']

        if not is_president:
            return jsonify({'success': False, 'error': 'Only the President can select cards for this exchange'})

        # Get president and culo data
        president_data = game_state['players'][game_state['card_exchange']['president_id']]
        culo_data = game_state['players'][game_state['card_exchange']['culo_id']]

        # Handle president's selection based on phase
        if phase == 'receive':
            # President is selecting cards to receive from Culo
            # Validate card index is within Culo's hand
            if not (0 <= card_index < len(culo_data['hand'])):
                return jsonify({'success': False, 'error': 'Invalid card index for Culo\'s hand'})

            # Add to president's selection for receiving
            game_state['card_exchange']['president_cards_to_receive'].append(card_index)

            # If president has selected 2 cards to receive, move to give phase
            if len(game_state['card_exchange']['president_cards_to_receive']) >= 2:
                game_state['card_exchange']['phase'] = 'give'

                # Sort indices in descending order to avoid shifting issues when removing
                game_state['card_exchange']['president_cards_to_receive'].sort(reverse=True)

                # Add system message
                president_name = president_data['name']
                add_system_message(f"👑 {president_name} (President) has selected 2 cards to receive from Culo", "info")

                # Save game state after president selects cards to receive
                save_game_state()

                return jsonify({
                    'success': True,
                    'message': 'Cards selected to receive',
                    'next_phase': 'give'
                })
            else:
                # Still need to select more cards
                return jsonify({
                    'success': True,
                    'message': 'First card selected, please select one more card',
                    'cards_selected': len(game_state['card_exchange']['president_cards_to_receive']),
                    'cards_needed': 2
                })

        elif phase == 'give':
            # President is selecting cards to give to Culo
            # Validate card index is within President's hand
            if not (0 <= card_index < len(president_data['hand'])):
                return jsonify({'success': False, 'error': 'Invalid card index for President\'s hand'})

            # Add to president's selection for giving
            game_state['card_exchange']['president_cards_to_give'].append(card_index)

            # If president has selected 2 cards to give, perform the exchange
            if len(game_state['card_exchange']['president_cards_to_give']) >= 2:
                # Sort indices in descending order to avoid shifting issues when removing
                game_state['card_exchange']['president_cards_to_give'].sort(reverse=True)

                # Perform the exchange
                # First, get the cards the president will receive
                cards_to_president = []
                for idx in game_state['card_exchange']['president_cards_to_receive']:
                    cards_to_president.append(culo_data['hand'][idx])

                # Remove cards from culo's hand (in reverse order to avoid index shifting)
                for idx in game_state['card_exchange']['president_cards_to_receive']:
                    culo_data['hand'].pop(idx)

                # Get the cards the culo will receive
                cards_to_culo = []
                for idx in game_state['card_exchange']['president_cards_to_give']:
                    cards_to_culo.append(president_data['hand'][idx])

                # Remove cards from president's hand (in reverse order to avoid index shifting)
                for idx in game_state['card_exchange']['president_cards_to_give']:
                    president_data['hand'].pop(idx)

                # Add the exchanged cards to each player's hand
                president_data['hand'].extend(cards_to_president)
                culo_data['hand'].extend(cards_to_culo)

                # Sort both players' hands after the exchange
                president_data['hand'] = sort_cards(president_data['hand'])
                culo_data['hand'] = sort_cards(culo_data['hand'])

                # Mark president exchange as completed
                game_state['card_exchange']['president_exchange_completed'] = True

                # Add system message
                culo_name = culo_data['name']
                president_name = president_data['name']
                add_system_message(
                    f"🔄 Card exchange completed between {president_name} (President) and {culo_name} (Culo)!", "success")

                # Check if we need to move to vice exchange
                if game_state['card_exchange']['vice_president_id'] and game_state['card_exchange']['vice_culo_id']:
                    game_state['card_exchange']['current_exchange'] = 'vice'
                    game_state['card_exchange']['phase'] = 'receive'
                    add_system_message(f"🔄 Now Vice-President and Vice-Culo will exchange 1 card each.", "info")
                else:
                    # No vice exchange needed, mark everything as completed
                    game_state['card_exchange']['completed'] = True

                # Save game state after president exchange is completed
                save_game_state()

                return jsonify({
                    'success': True,
                    'message': 'President-Culo card exchange completed',
                    'next_exchange': game_state['card_exchange']['current_exchange']
                })
            else:
                # Still need to select more cards
                return jsonify({
                    'success': True,
                    'message': 'First card selected, please select one more card',
                    'cards_selected': len(game_state['card_exchange']['president_cards_to_give']),
                    'cards_needed': 2
                })

    elif exchange_type == 'vice':
        # Vice-President-Vice-Culo exchange (1 card each)
        # Check if player is vice-president
        is_vice_president = player_id == game_state['card_exchange']['vice_president_id']

        if not is_vice_president:
            return jsonify({'success': False, 'error': 'Only the Vice-President can select cards for this exchange'})

        # Get vice-president and vice-culo data
        vice_president_data = game_state['players'][game_state['card_exchange']['vice_president_id']]
        vice_culo_data = game_state['players'][game_state['card_exchange']['vice_culo_id']]

        # Handle vice-president's selection based on phase
        if phase == 'receive':
            # Vice-President is selecting a card to receive from Vice-Culo
            # Validate card index is within Vice-Culo's hand
            if not (0 <= card_index < len(vice_culo_data['hand'])):
                return jsonify({'success': False, 'error': 'Invalid card index for Vice-Culo\'s hand'})

            # Store vice-president's selection for receiving
            game_state['card_exchange']['vice_president_card_to_receive'] = card_index
            game_state['card_exchange']['phase'] = 'give'

            # Add system message
            vice_president_name = vice_president_data['name']
            add_system_message(
                f"🥈 {vice_president_name} (Vice-President) has selected a card to receive from Vice-Culo", "info")

            # Save game state after vice president selects card to receive
            save_game_state()

            return jsonify({
                'success': True,
                'message': 'Card selected to receive',
                'next_phase': 'give'
            })

        elif phase == 'give':
            # Vice-President is selecting a card to give to Vice-Culo
            # Validate card index is within Vice-President's hand
            if not (0 <= card_index < len(vice_president_data['hand'])):
                return jsonify({'success': False, 'error': 'Invalid card index for Vice-President\'s hand'})

            # Store vice-president's selection for giving
            game_state['card_exchange']['vice_president_card_to_give'] = card_index

            # Perform the exchange
            vice_president_give_index = game_state['card_exchange']['vice_president_card_to_give']
            vice_culo_give_index = game_state['card_exchange']['vice_president_card_to_receive']

            # Get the selected cards
            vice_president_card = vice_president_data['hand'][vice_president_give_index]
            vice_culo_card = vice_culo_data['hand'][vice_culo_give_index]

            # Swap the cards
            vice_president_data['hand'][vice_president_give_index] = vice_culo_card
            vice_culo_data['hand'][vice_culo_give_index] = vice_president_card

            # Sort both players' hands after the exchange
            vice_president_data['hand'] = sort_cards(vice_president_data['hand'])
            vice_culo_data['hand'] = sort_cards(vice_culo_data['hand'])

            # Mark exchange as completed
            game_state['card_exchange']['vice_exchange_completed'] = True
            game_state['card_exchange']['completed'] = True

            # Add system message
            vice_culo_name = vice_culo_data['name']
            vice_president_name = vice_president_data['name']
            add_system_message(
                f"🔄 Card exchange completed between {vice_president_name} (Vice-President) and {vice_culo_name} (Vice-Culo)!", "success")
            add_system_message(f"🎮 All card exchanges completed! The game will now begin.", "success")

            # Save game state after vice exchange is completed
            save_game_state()

            return jsonify({
                'success': True,
                'message': 'Vice-President-Vice-Culo card exchange completed'
            })

    else:
        return jsonify({'success': False, 'error': 'Invalid exchange type'})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
