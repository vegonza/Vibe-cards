import re
import uuid
from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from culo_game.models.game_state import GameState
from culo_game.models.card import sort_cards
from culo_game.models.game_manager import GameManager

# Create blueprint
player_bp = Blueprint('player', __name__)


@player_bp.route('/')
def index():
    """Show join page or redirect to game if already joined"""
    # If player is already in the game, redirect to game page
    player_id = session.get('player_id')
    game_state = GameState()

    if player_id and player_id in game_state.data['players']:
        return redirect(url_for('game.game_page'))

    # Otherwise show the join page
    return render_template('join.html')


@player_bp.route('/join', methods=['GET', 'POST'])
def join_game():
    """Handle player joining the game"""
    error = None
    game_state = GameState()

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
            if len(game_state.data['players']) >= 12:
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
            existing_positions = [player_data['position'] for player_data in game_state.data['players'].values()]

            # Find the first available position
            position_order = [0, 2, 3, 1, 4, 6, 7, 5, 8, 9, 10, 11]  # Clockwise order starting from bottom
            player_position = next((pos for pos in position_order if pos not in existing_positions),
                                   len(game_state.data['players']))

            # Check if this is the first player (host)
            is_host = len(game_state.data['players']) == 0 or game_state.data['host_player_id'] is None
            if is_host:
                game_state.data['host_player_id'] = player_id

            # Initialize player in game state
            game_state.data['players'][player_id] = {
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
                game_state.add_system_message(f"👑 {player_name} has joined as the host!", "info")
            else:
                game_state.add_system_message(f"👋 {player_name} has joined the game!", "info")

            # If the game has already started, add the new player to the game
            if game_state.data['started']:
                # Give cards to the new player without disrupting the game
                GameManager.redistribute_cards()

            # If the game hasn't started and we have at least 2 players, start it
            elif not game_state.data['started'] and len(game_state.data['players']) >= 2:
                GameManager.start_game()

            # Save game state after player joins
            game_state.save_state()

            # Redirect to game page
            return redirect(url_for('game.game_page'))

    # Show join page with error if any
    return render_template('join.html', error=error)


@player_bp.route('/assign_roles', methods=['POST'])
def assign_roles():
    """Assign roles to players (host only)"""
    player_id = session.get('player_id')
    game_state = GameState()

    # Check if player is the host
    if player_id != game_state.data['host_player_id']:
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

        if target_player_id in game_state.data['players'] and role in ['neutral', 'president', 'vice-president', 'vice-culo', 'culo']:
            game_state.data['players'][target_player_id]['role'] = role

    # Add system message
    host_name = game_state.data['players'][game_state.data['host_player_id']]['name']
    game_state.add_system_message(f"👑 {host_name} (host) has assigned player roles!", "info")

    # Save game state after role assignment
    game_state.save_state()

    return jsonify({
        'success': True
    })


@player_bp.route('/assign_ranks', methods=['POST'])
def assign_ranks():
    """Assign ranks to players (host only)"""
    player_id = session.get('player_id')
    game_state = GameState()

    # Check if player is the host
    if player_id != game_state.data['host_player_id']:
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

        if target_player_id in game_state.data['players'] and rank in ['gold', 'silver', 'bronze', 'loser', None]:
            game_state.data['players'][target_player_id]['rank'] = rank

            # Add to rankings list if not already there
            if rank and target_player_id not in game_state.data['rankings']:
                game_state.data['rankings'].append(target_player_id)
            # Remove from rankings if rank is None
            elif not rank and target_player_id in game_state.data['rankings']:
                game_state.data['rankings'].remove(target_player_id)

    # Add system message
    host_name = game_state.data['players'][game_state.data['host_player_id']]['name']
    game_state.add_system_message(f"👑 {host_name} (host) has manually assigned player ranks!", "info")

    # Save game state after rank assignment
    game_state.save_state()

    return jsonify({
        'success': True
    })
