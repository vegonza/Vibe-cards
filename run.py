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

from game_logic.utils import (
    init_game_state,
    util_create_deck,
    util_sort_cards,
    util_add_system_message,
    util_get_players_data,
    util_assign_automatic_roles,
    util_get_player_by_position,
)
from game_logic.actions import (
    start_game as action_start_game,
    redistribute_cards as action_redistribute_cards,
    play_card_logic,
    skip_turn_logic,
    reset_game_logic,
    exchange_card_logic,
    advance_to_next_player
)

app = Flask(__name__, static_folder='app/static', template_folder='app/templates')
app.secret_key = os.urandom(24)

GAME_STATE_FILE = 'game_state.pickle'
TURN_TIMER_DURATION = 15
game_state = init_game_state()


def save_game_state():
    try:
        with open(GAME_STATE_FILE, 'wb') as f:
            pickle.dump(game_state, f)
        return True
    except Exception as e:
        print(f"Error saving game state: {e}")
        return False


def load_game_state():
    global game_state
    try:
        if os.path.exists(GAME_STATE_FILE):
            with open(GAME_STATE_FILE, 'rb') as f:
                loaded_state = pickle.load(f)
                current_host = game_state.get('host_player_id')

                game_state.clear()
                game_state.update(init_game_state())
                game_state.update(loaded_state)

                if 'host_player_id' not in game_state or game_state['host_player_id'] is None:
                    if current_host:
                        game_state['host_player_id'] = current_host
                    elif game_state['players'] and game_state['players'].keys():
                        game_state['host_player_id'] = list(game_state['players'].keys())[0]

                default_state_for_keys = init_game_state()
                for key, default_value in default_state_for_keys.items():
                    if key not in game_state:
                        game_state[key] = default_value
                    elif isinstance(default_value, dict):
                        if not isinstance(game_state[key], dict):
                            game_state[key] = {}
                        for sub_key, sub_default_value in default_value.items():
                            if sub_key not in game_state[key]:
                                game_state[key][sub_key] = sub_default_value

                util_add_system_message(game_state, "🔄 Game state loaded from saved file.", "info")
                return True
    except Exception as e:
        print(f"Error loading game state: {e} - Reinitializing game state.")
        game_state.clear()
        game_state.update(init_game_state())
    return False


def create_deck(deck_size=None):
    return util_create_deck(game_state, deck_size)


def sort_cards(cards):
    return util_sort_cards(cards)


def add_system_message(message, message_type="info"):
    return util_add_system_message(game_state, message, message_type)


def get_players_data():
    return util_get_players_data(game_state)


def get_player_by_position(position):
    return util_get_player_by_position(game_state, position)


def assign_automatic_roles():
    return util_assign_automatic_roles(game_state, save_game_state_func=save_game_state)


load_game_state()


@app.route('/')
def index():
    player_id = session.get('player_id')
    if player_id and player_id in game_state['players']:
        return redirect(url_for('game'))
    return render_template('join.html')


@app.route('/join', methods=['GET', 'POST'])
def join_game():
    error = None
    if request.method == 'POST':
        player_name = request.form.get('player_name', '').strip()
        if not player_name:
            error = "Please enter a name."
        elif len(player_name) > 20:
            error = "Name must be 20 characters or less."
        elif not re.match(r'^[a-zA-Z0-9 _-]+$', player_name):
            error = "Name can only contain letters, numbers, spaces, underscores, and hyphens."
        else:
            if len(game_state['players']) >= 12:
                error = "Game is full. Please wait for a spot to open."
                return render_template('join.html', error=error)

            player_id = str(uuid.uuid4())
            session['player_id'] = player_id

            existing_positions = [p_data['position'] for p_data in game_state['players'].values()]
            position_order = [0, 2, 3, 1, 4, 6, 7, 5, 8, 9, 10, 11]
            player_position = next((pos for pos in position_order if pos not in existing_positions),
                                   len(game_state['players']))

            is_host = not game_state['players'] or game_state['host_player_id'] is None
            if is_host:
                game_state['host_player_id'] = player_id

            game_state['players'][player_id] = {
                'name': player_name, 'hand': [], 'position': player_position,
                'skipped': False, 'rank': None, 'is_host': is_host, 'role': 'neutral'
            }

            system_message_text = f"👑 {player_name} has joined as the host!" if is_host else f"👋 {player_name} has joined the game!"
            add_system_message(system_message_text, "info")

            if game_state['started']:
                action_redistribute_cards(game_state, save_game_state)
            # Remove automatic game start when 2+ players join
            # Instead, we'll wait for the host to explicitly start the game

            save_game_state()
            return redirect(url_for('game'))

    return render_template('join.html', error=error)


@app.route('/game')
def game():
    player_id = session.get('player_id')
    if not player_id:
        return redirect(url_for('index'))
    if player_id not in game_state['players']:
        session.pop('player_id', None)
        return redirect(url_for('index'))

    player_data = game_state['players'][player_id]
    all_players_data = get_players_data()
    is_my_turn = game_state['current_player_index'] == player_data['position']
    top_card = game_state['table'][-1] if game_state['table'] else None

    can_play = False
    playable_cards_indices = []
    if is_my_turn and not player_data['skipped'] and player_data['rank'] is None:
        if not game_state['card_exchange'].get('active', False) or game_state['card_exchange'].get('completed', False):
            if not top_card:
                can_play = len(player_data['hand']) > 0
                playable_cards_indices = list(range(len(player_data['hand'])))
            else:
                for i, card_in_hand in enumerate(player_data['hand']):
                    if card_in_hand['value'] == '2' or card_in_hand['numeric_value'] >= top_card['numeric_value']:
                        can_play = True
                        playable_cards_indices.append(i)

    return render_template(
        'game.html',
        player_hand=sort_cards(player_data['hand']),
        table=game_state['table'], player_name=player_data['name'], players=all_players_data,
        is_my_turn=is_my_turn, current_player_index=game_state['current_player_index'],
        can_play=can_play, playable_cards=playable_cards_indices, top_card=top_card,
        game_name=game_state['game_name'], last_action=game_state['last_action'],
        chat_messages=game_state['chat_messages'], required_cards_to_play=game_state['required_cards_to_play']
    )


@app.route('/play_card', methods=['POST'])
def play_card_route():
    player_id = session.get('player_id')
    if not player_id or player_id not in game_state['players']:
        return jsonify({'success': False, 'error': 'Player not found or not in session'})
    data = request.get_json()
    card_indices = [data.get('card_index')] if 'card_index' in data else data.get('card_indices', [])
    joker_value = data.get('joker_value')
    result = play_card_logic(game_state, player_id, card_indices, joker_value, save_game_state)
    return jsonify(result)


@app.route('/skip_turn', methods=['POST'])
def skip_turn_route():
    player_id = session.get('player_id')
    if not player_id or player_id not in game_state['players']:
        return jsonify({'success': False, 'error': 'Player not found or not in session'})
    result = skip_turn_logic(game_state, player_id, save_game_state)
    return jsonify(result)


@app.route('/reset_game', methods=['POST'])
def reset_game_route():
    player_id = session.get('player_id')
    if player_id != game_state.get('host_player_id'):
        return jsonify({'success': False, 'error': 'Only the host can reset the game'})
    result = reset_game_logic(game_state, save_game_state)
    return jsonify(result)


@app.route('/start_game', methods=['POST'])
def start_game_route():
    player_id = session.get('player_id')
    if player_id != game_state.get('host_player_id'):
        return jsonify({'success': False, 'error': 'Only the host can start the game'})

    if len(game_state['players']) < 2:
        return jsonify({'success': False, 'error': 'Need at least 2 players to start the game'})

    if game_state['started']:
        return jsonify({'success': False, 'error': 'Game has already started'})

    game_state['waiting_for_start'] = False
    action_start_game(game_state, save_game_state)
    host_name = game_state['players'][game_state['host_player_id']]['name']
    add_system_message(f"🎮 {host_name} (host) has started the game!", "success")
    save_game_state()
    return jsonify({'success': True, 'refresh': True})


@app.route('/get_game_state')
def get_game_state_route():
    player_id = session.get('player_id')
    if not player_id or player_id not in game_state['players']:
        return jsonify({'success': False, 'error': 'Player not found or invalid session.'})

    player_data_initial = game_state['players'][player_id]
    is_host = player_id == game_state.get('host_player_id')
    turn_timer_info = None

    if game_state.get('turn_start_time') is not None and \
       not game_state.get('game_over', False) and \
       (not game_state['card_exchange'].get('active', False) or game_state['card_exchange'].get('completed', False)):
        elapsed_time = time.time() - game_state['turn_start_time']
        time_left = max(0, TURN_TIMER_DURATION - elapsed_time)
        turn_timer_info = {
            'duration': TURN_TIMER_DURATION,
            'time_left': time_left,
            'percentage': (time_left / TURN_TIMER_DURATION) * 100 if TURN_TIMER_DURATION > 0 else 0
        }

        current_player_data_for_skip_check = get_player_by_position(game_state['current_player_index'])
        if current_player_data_for_skip_check and time_left <= 0:
            cp_id_for_skip = None
            for pid_loop, pd_loop in game_state['players'].items():
                if pd_loop['position'] == game_state['current_player_index']:
                    cp_id_for_skip = pid_loop
                    break

            if cp_id_for_skip and not game_state['players'][cp_id_for_skip]['skipped'] and game_state['players'][cp_id_for_skip]['rank'] is None:
                timed_out_player = game_state['players'][cp_id_for_skip]
                game_state['last_skipped_position'] = game_state['current_player_index']

                # Attempt to add 3 cards to the player's hand
                full_deck = util_create_deck(game_state)
                cards_in_play = set()
                for p_data in game_state['players'].values():
                    for card in p_data['hand']:
                        cards_in_play.add((card['value'], card['suit']))
                for card in game_state['table']:
                    cards_in_play.add((card['value'], card['suit']))

                available_cards = [
                    card for card in full_deck if (card['value'], card['suit']) not in cards_in_play
                ]

                if len(available_cards) >= 3:
                    cards_to_add = random.sample(available_cards, 3)
                    timed_out_player['hand'].extend(cards_to_add)
                    timed_out_player['hand'] = util_sort_cards(timed_out_player['hand'])
                    util_add_system_message(
                        game_state,
                        f"⏳ {timed_out_player['name']} timed out and received 3 extra cards!",
                        "warning"
                    )
                    game_state['last_action'] = f"{timed_out_player['name']} timed out and received 3 cards"
                else:
                    util_add_system_message(
                        game_state,
                        f"⏳ {timed_out_player['name']} timed out! (Not enough cards in deck to penalize).",
                        "warning"
                    )
                    game_state['last_action'] = f"{timed_out_player['name']} timed out"

                advance_to_next_player(game_state, save_game_state)
                save_game_state()
                player_data_initial = game_state['players'][player_id]

    player_data = game_state['players'][player_id]
    is_my_turn = game_state['current_player_index'] == player_data['position']
    all_players_data = get_players_data()
    can_play = False
    playable_cards_indices = []
    top_card = game_state['table'][-1] if game_state['table'] else None

    if not game_state['card_exchange'].get('active', False) or game_state['card_exchange'].get('completed', False):
        if is_my_turn and not player_data['skipped'] and player_data['rank'] is None:
            if not top_card:
                can_play = len(player_data['hand']) > 0
                playable_cards_indices = list(range(len(player_data['hand'])))
            else:
                for i, card_in_hand in enumerate(player_data['hand']):
                    if card_in_hand['value'] == '2' or card_in_hand['numeric_value'] >= top_card['numeric_value']:
                        can_play = True
                        playable_cards_indices.append(i)

    rankings_display_info = []
    for rank_idx, p_id_ranked in enumerate(game_state.get('rankings', [])):
        if p_id_ranked in game_state['players']:
            ranked_player_data = game_state['players'][p_id_ranked]
            rank_map = {0: 'gold', 1: 'silver', 2: 'bronze'}
            actual_rank_name = rank_map.get(rank_idx, 'loser')
            rankings_display_info.append({
                'player_id': p_id_ranked, 'player_name': ranked_player_data['name'],
                'rank': actual_rank_name, 'position': rank_idx + 1
            })

    card_exchange_display_info = None
    if game_state['card_exchange'].get('active', False):
        exchange_hands_info = {}
        ce_data = game_state['card_exchange']
        is_president_for_exchange = player_id == ce_data.get('president_id')
        is_vice_president_for_exchange = player_id == ce_data.get('vice_president_id')
        if ce_data['current_exchange'] == 'president' and is_president_for_exchange and ce_data['phase'] == 'receive':
            culo_player_id = ce_data.get('culo_id')
            if culo_player_id and culo_player_id in game_state['players']:
                exchange_hands_info['culo_hand'] = sort_cards(game_state['players'][culo_player_id]['hand'])
        elif ce_data['current_exchange'] == 'vice' and is_vice_president_for_exchange and ce_data['phase'] == 'receive':
            vice_culo_player_id = ce_data.get('vice_culo_id')
            if vice_culo_player_id and vice_culo_player_id in game_state['players']:
                exchange_hands_info['vice_culo_hand'] = sort_cards(game_state['players'][vice_culo_player_id]['hand'])
        card_exchange_display_info = {**ce_data, **exchange_hands_info,
                                      'is_president': is_president_for_exchange,
                                      'is_culo': player_id == ce_data.get('culo_id'),
                                      'is_vice_president': is_vice_president_for_exchange,
                                      'is_vice_culo': player_id == ce_data.get('vice_culo_id')}

    # Prepare the response data
    response_data = {
        'success': True,
        'player_hand': sort_cards(player_data['hand']),
        'table': game_state['table'],
        'players': all_players_data,
        'is_my_turn': is_my_turn,
        'current_player_index': game_state['current_player_index'],
        'can_play': can_play,
        'playable_cards': playable_cards_indices,
        'top_card': top_card,
        'game_name': game_state['game_name'],
        'last_action': game_state['last_action'],
        'chat_messages': game_state['chat_messages'],
        'required_cards_to_play': game_state['required_cards_to_play'],
        'rankings': rankings_display_info,
        'is_host': player_id == game_state.get('host_player_id'),
        'my_name': player_data['name'],
        'game_over': game_state.get('game_over', False),
        'winner': game_state.get('winner'),
        'deck_size': game_state.get('deck_size', 1),
        'waiting_for_start': game_state.get('waiting_for_start', False),
        'card_exchange': card_exchange_display_info,
        'turn_timer': turn_timer_info,
        'last_skipped_position': game_state.pop('last_skipped_position', None),
        'last_card_played': game_state.get('last_card_played'),
        'deal_animation_pending': game_state.get('deal_animation_pending', False)
    }

    return jsonify(response_data)


@app.route('/send_message', methods=['POST'])
def send_message():
    player_id = session.get('player_id')
    if not player_id or player_id not in game_state['players']:
        return jsonify({'success': False, 'error': 'Player not found or not in session'})
    player_name = game_state['players'][player_id]['name']
    data = request.get_json()
    message_text = data.get('message', '').strip()
    if not message_text:
        return jsonify({'success': False, 'error': 'Message cannot be empty'})
    if len(message_text) > 200:
        return jsonify({'success': False, 'error': 'Message too long (max 200 chars)'})
    timestamp = datetime.now().strftime('%H:%M')
    chat_message = {'sender': player_name, 'text': message_text, 'timestamp': timestamp, 'id': str(uuid.uuid4())}
    game_state['chat_messages'].append(chat_message)
    if len(game_state['chat_messages']) > 50:
        game_state['chat_messages'] = game_state['chat_messages'][-50:]
    if len(game_state['chat_messages']) % 5 == 0:
        save_game_state()
    return jsonify({'success': True})


@app.route('/assign_roles', methods=['POST'])
def assign_roles_route():
    player_id = session.get('player_id')
    if player_id != game_state.get('host_player_id'):
        return jsonify({'success': False, 'error': 'Only the host can assign roles'})
    data = request.get_json()
    roles_to_assign = data.get('roles', [])
    if not roles_to_assign:
        return jsonify({'success': False, 'error': 'No roles provided'})
    valid_roles = ['neutral', 'president', 'vice-president', 'vice-culo', 'culo']
    for role_info in roles_to_assign:
        target_p_id = role_info.get('player_id')
        new_role = role_info.get('role')
        if target_p_id in game_state['players'] and new_role in valid_roles:
            game_state['players'][target_p_id]['role'] = new_role
    host_name = game_state['players'][game_state['host_player_id']]['name']
    add_system_message(f"👑 {host_name} (host) has assigned player roles!", "info")
    save_game_state()
    return jsonify({'success': True})


@app.route('/assign_ranks', methods=['POST'])
def assign_ranks_route():
    player_id = session.get('player_id')
    if player_id != game_state.get('host_player_id'):
        return jsonify({'success': False, 'error': 'Only the host can assign ranks'})
    data = request.get_json()
    ranks_to_assign = data.get('ranks', [])
    if not ranks_to_assign:
        return jsonify({'success': False, 'error': 'No ranks provided'})
    valid_ranks = ['gold', 'silver', 'bronze', 'loser', None]
    for rank_info in ranks_to_assign:
        target_p_id = rank_info.get('player_id')
        new_rank = rank_info.get('rank')
        if target_p_id in game_state['players'] and new_rank in valid_ranks:
            game_state['players'][target_p_id]['rank'] = new_rank
            if new_rank and target_p_id not in game_state['rankings']:
                game_state['rankings'].append(target_p_id)
            elif not new_rank and target_p_id in game_state['rankings']:
                game_state['rankings'].remove(target_p_id)
    host_name = game_state['players'][game_state['host_player_id']]['name']
    add_system_message(f"👑 {host_name} (host) has manually assigned player ranks!", "info")
    save_game_state()
    return jsonify({'success': True})


@app.route('/change_deck_size', methods=['POST'])
def change_deck_size_route():
    player_id = session.get('player_id')
    if player_id != game_state.get('host_player_id'):
        return jsonify({'success': False, 'error': 'Only the host can change the deck size'})
    data = request.get_json()
    new_deck_size_req = data.get('deck_size')
    try:
        new_deck_size = float(new_deck_size_req)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid deck size format.'})
    valid_deck_sizes = [0.25, 0.5, 1.0, 2.0, 3.0]
    if new_deck_size not in valid_deck_sizes:
        return jsonify({'success': False, 'error': f'Invalid deck size. Valid options are {valid_deck_sizes}'})

    try:  # Ensure deck_size is a number
        new_deck_size = float(new_deck_size_req)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid deck size format.'})

    valid_deck_sizes = [0.25, 0.5, 1.0, 2.0, 3.0]  # Use floats for comparison
    if new_deck_size not in valid_deck_sizes:
        return jsonify({'success': False, 'error': f'Invalid deck size. Valid options are {valid_deck_sizes}'})

    game_state['deck_size'] = new_deck_size
    host_name = game_state['players'][game_state['host_player_id']]['name']
    size_map = {0.25: "1/4", 0.5: "1/2", 1.0: "1", 2.0: "2", 3.0: "3"}
    deck_size_text = size_map.get(new_deck_size, str(new_deck_size))

    add_system_message(f"🃏 {host_name} changed the deck size to {deck_size_text} deck(s)!", "info")  # Use wrapper
    save_game_state()
    return jsonify({'success': True})


@app.route('/exchange_card', methods=['POST'])
def exchange_card():
    player_id = session.get('player_id')
    if not player_id or player_id not in game_state['players']:
        return jsonify({'success': False, 'error': 'Player not found or not in session'})

    data = request.get_json()
    card_idx_req = data.get('card_index')
    phase_req = data.get('phase')
    exchange_type_req = data.get('exchange_type', game_state['card_exchange'].get('current_exchange'))

    # Validate card_index
    try:
        card_index = int(card_idx_req) if card_idx_req is not None else None
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid card index format.'})

    result = exchange_card_logic(game_state, player_id, card_index, phase_req, exchange_type_req, save_game_state)
    return jsonify(result)


@app.route('/kick_player', methods=['POST'])
def kick_player():
    # Check if the requesting player is the host
    host_player_id = session.get('player_id')
    if host_player_id != game_state.get('host_player_id'):
        return jsonify({'success': False, 'error': 'Only the host can kick players'})

    data = request.get_json()
    player_id_to_kick = data.get('player_id')

    # Check if the player exists
    if not player_id_to_kick or player_id_to_kick not in game_state['players']:
        return jsonify({'success': False, 'error': 'Player not found'})

    # Cannot kick yourself (the host)
    if player_id_to_kick == host_player_id:
        return jsonify({'success': False, 'error': 'You cannot kick yourself'})

    # Get the player name before removing them
    kicked_player_name = game_state['players'][player_id_to_kick]['name']
    host_name = game_state['players'][host_player_id]['name']

    # Remove the player from the game
    del game_state['players'][player_id_to_kick]

    # If the player was in rankings, remove them
    if player_id_to_kick in game_state.get('rankings', []):
        game_state['rankings'].remove(player_id_to_kick)

    # Add system message
    add_system_message(f"👢 {host_name} kicked {kicked_player_name} from the game!", "warning")

    # If the game is in progress, redistribute cards
    if game_state['started'] and len(game_state['players']) >= 2:
        action_redistribute_cards(game_state, save_game_state)

    # Save game state
    save_game_state()

    return jsonify({
        'success': True,
        'kicked_player_name': kicked_player_name,
        'refresh': True
    })


if __name__ == '__main__':
    # Ensure game_state is loaded before running
    if not os.path.exists(GAME_STATE_FILE):
        save_game_state()  # Save a default state if no file exists
    else:
        load_game_state()  # Load existing state

    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=False)
