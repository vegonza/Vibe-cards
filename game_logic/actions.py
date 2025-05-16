import random
import time
import uuid

from .utils import (
    util_create_deck, util_sort_cards, util_add_system_message,
    util_get_player_by_position, util_assign_automatic_roles, CARD_VALUES
)


def start_game(game_state, save_game_state_func):
    """Start the game by dealing cards to all players"""
    deck = util_create_deck(game_state)  # Uses util create_deck, passing game_state
    random.shuffle(deck)

    num_players = len(game_state['players'])
    if num_players == 0:  # Cannot start game with no players
        return

    cards_per_player = len(deck) // num_players

    sorted_players = sorted(game_state['players'].items(), key=lambda x: x[1]['position'])

    game_state['rankings'] = []
    game_state['current_game_players'] = [player_id for player_id, _ in sorted_players]

    for i, (player_id, player_data) in enumerate(sorted_players):
        start_idx = i * cards_per_player
        end_idx = (i + 1) * cards_per_player if i < num_players - 1 else len(deck)
        player_data['hand'] = deck[start_idx:end_idx]
        player_data['hand'] = util_sort_cards(player_data['hand'])
        player_data['skipped'] = False
        player_data['rank'] = None

    game_state['started'] = True
    position_order = [0, 2, 3, 1, 4, 6, 7, 5, 8, 9, 10, 11]
    player_positions = [player['position'] for player in game_state['players'].values()]
    first_player_position = next((pos for pos in position_order if pos in player_positions), 0)
    game_state['current_player_index'] = first_player_position

    game_state['table'] = []
    game_state['last_card_played'] = None
    game_state['last_action'] = None
    game_state['chat_messages'] = []
    game_state['turn_start_time'] = time.time()

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

    if president_id and culo_id:
        game_state['card_exchange'].update({
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
        })
        util_add_system_message(
            game_state, f"🔄 Card exchange is now active! President takes 2 cards from Culo and gives 2 cards back.", "info")
        if vice_president_id and vice_culo_id:
            util_add_system_message(
                game_state, f"🔄 Vice-President and Vice-Culo will exchange 1 card each after the President's exchange.", "info")
    else:
        game_state['card_exchange'].update({
            'active': False, 'president_id': None, 'culo_id': None, 'vice_president_id': None, 'vice_culo_id': None,
            'president_cards_to_receive': [], 'president_cards_to_give': [], 'vice_president_card_to_receive': None,
            'vice_president_card_to_give': None, 'president_exchange_completed': False, 'vice_exchange_completed': False,
            'completed': False, 'current_exchange': 'president', 'phase': 'receive'
        })

    player_names = [player['name'] for player in game_state['players'].values()]
    util_add_system_message(game_state, f"🎮 Game started with players: {', '.join(player_names)}", "success")
    save_game_state_func()


def redistribute_cards(game_state, save_game_state_func):
    """Redistribute all cards when a new player joins"""
    new_player_id = None
    new_player_data = None
    for player_id, player_data_val in game_state['players'].items():
        if len(player_data_val['hand']) == 0 and player_data_val['rank'] is None:
            new_player_id = player_id
            new_player_data = player_data_val
            break
    if not new_player_id:
        return

    new_player_cards = util_create_deck(game_state)  # Uses util create_deck
    random.shuffle(new_player_cards)

    total_cards = 0
    active_players = 0
    for player_id, player_data_val in game_state['players'].items():
        if player_id != new_player_id and player_data_val['rank'] is None:
            total_cards += len(player_data_val['hand'])
            active_players += 1

    cards_for_new_player = len(new_player_cards) if active_players == 0 else total_cards // active_players
    cards_for_new_player = max(cards_for_new_player, 5)
    new_player_data['hand'] = new_player_cards[:cards_for_new_player]
    new_player_data['hand'] = util_sort_cards(new_player_data['hand'])

    if new_player_id not in game_state['current_game_players']:
        game_state['current_game_players'].append(new_player_id)

    util_add_system_message(
        game_state, f"🃏 {new_player_data['name']} has been dealt {len(new_player_data['hand'])} cards and joined the game in progress!", "info")
    save_game_state_func()


def play_card_logic(game_state, player_id, card_indices, joker_value, save_game_state_func):
    player_data = game_state['players'][player_id]

    if game_state['current_player_index'] != player_data['position']:
        return {'success': False, 'error': 'Not your turn'}
    if player_data['skipped']:
        return {'success': False, 'error': 'You have already skipped your turn'}
    if not card_indices:
        return {'success': False, 'error': 'No cards selected'}
    if len(card_indices) != game_state['required_cards_to_play'] and len(game_state['table']) > 0:
        return {'success': False, 'error': f'You must play exactly {game_state["required_cards_to_play"]} card(s)'}
    for idx in card_indices:
        if not (0 <= idx < len(player_data['hand'])):
            return {'success': False, 'error': 'Invalid card index'}

    if len(card_indices) > 1:
        reference_value = None
        is_playing_only_jokers = True
        temp_selected_cards_from_hand = [player_data['hand'][idx] for idx in card_indices]
        for card_in_hand in temp_selected_cards_from_hand:
            if card_in_hand['value'] != '2':
                reference_value = card_in_hand['value']
                is_playing_only_jokers = False
                break
        if is_playing_only_jokers:
            reference_value = joker_value if joker_value else '2'
        elif not reference_value:
            return {'success': False, 'error': 'Error determining reference value for multi-card play.'}
        for card_in_hand in temp_selected_cards_from_hand:
            card_original_value = card_in_hand['value']
            effective_value = card_original_value
            if card_original_value == '2':
                if joker_value:
                    effective_value = joker_value
                elif not is_playing_only_jokers:
                    effective_value = reference_value
            if effective_value != reference_value:
                return {'success': False, 'error': 'Selected cards must have the same value (considering jokers).'}

    selected_cards_from_hand = [player_data['hand'][idx] for idx in card_indices]
    effective_play_value_for_comparison = None
    if joker_value:
        effective_play_value_for_comparison = CARD_VALUES.get(joker_value)
    elif len(selected_cards_from_hand) > 0:
        first_card = selected_cards_from_hand[0]
        if first_card['value'] != '2':
            effective_play_value_for_comparison = first_card['numeric_value']
        elif not any(c['value'] != '2' for c in selected_cards_from_hand):
            effective_play_value_for_comparison = CARD_VALUES['2']
        else:
            non_joker_in_selection = next((c['value'] for c in selected_cards_from_hand if c['value'] != '2'), None)
            if non_joker_in_selection:
                effective_play_value_for_comparison = CARD_VALUES.get(non_joker_in_selection)
            else:
                effective_play_value_for_comparison = CARD_VALUES['2']

    top_card = game_state['table'][-1] if game_state['table'] else None
    is_valid_play = False
    if not top_card:
        is_valid_play = True
        game_state['required_cards_to_play'] = len(selected_cards_from_hand)
    elif all(card['value'] == '2' for card in selected_cards_from_hand) and not joker_value:
        is_valid_play = True
    elif effective_play_value_for_comparison is not None and effective_play_value_for_comparison >= top_card['numeric_value']:
        is_valid_play = True

    if not is_valid_play:
        error_detail = f"Top card: {top_card['value'] if top_card else 'None'}. Your play (effective): {effective_play_value_for_comparison}. Joker_value provided: {joker_value}."
        return {'success': False, 'error': f'Invalid card(s). You must play card(s) with equal or higher value, or 2s. {error_detail}'}

    card_indices.sort(reverse=True)
    played_cards = []
    for idx in card_indices:
        played_card = player_data['hand'].pop(idx)
        played_card['id'] = str(uuid.uuid4())
        if played_card['value'] == '2' and joker_value:
            played_card['original_value'] = played_card['value']
            played_card['original_numeric_value'] = played_card['numeric_value']
            played_card['joker_value'] = joker_value
            played_card['display_value'] = joker_value
            if joker_value in CARD_VALUES:
                played_card['numeric_value'] = CARD_VALUES[joker_value]
        played_cards.append(played_card)

    player_data['hand'] = util_sort_cards(player_data['hand'])
    game_state['table'].extend(played_cards)
    game_state['last_card_played'] = played_cards[-1]['id']
    game_state['last_card_player_position'] = player_data['position']
    game_state['last_table_length'] = len(game_state['table'])

    previous_card_on_table = game_state['table'][-len(played_cards) -
                                                 1] if len(game_state['table']) > len(played_cards) else None

    if len(player_data['hand']) == 0:
        if player_id not in game_state['rankings']:
            game_state['rankings'].append(player_id)
        rank_position = game_state['rankings'].index(player_id)
        rank_map = {0: ('gold', "🥇 Gold"), 1: ('silver', "🥈 Silver"), 2: ('bronze', "🥉 Bronze")}
        player_data['rank'], rank_text = rank_map.get(rank_position, ('loser', "👎 Loser"))

        # Check for >1 to avoid issues with 1 player game
        if len(game_state['rankings']) == len(game_state['current_game_players']) - 1 and len(game_state['current_game_players']) > 1:
            last_player_id = next(
                (rem_id for rem_id in game_state['current_game_players'] if rem_id not in game_state['rankings']), None)
            if last_player_id and last_player_id in game_state['players']:
                game_state['rankings'].append(last_player_id)
                game_state['players'][last_player_id]['rank'] = 'loser'
                util_add_system_message(
                    game_state, f"👎 {game_state['players'][last_player_id]['name']} gets the Loser rank!", "warning")
                game_state['game_over'] = True
                util_add_system_message(game_state, f"🏁 Game over! All players have finished!", "success")

        if len(game_state['rankings']) == len(game_state['current_game_players']):
            game_state['game_over'] = True  # All players finished
            util_add_system_message(game_state, f"🏁 Game over! All players have finished!", "success")

        util_assign_automatic_roles(game_state, save_game_state_func)  # Pass game_state and save_func
        game_state['last_action'] = f"{player_data['name']} has finished with {rank_text} rank!"
        if game_state['game_over'] and game_state['rankings']:
            game_state['winner'] = game_state['rankings'][0]
        util_add_system_message(game_state, f"🏆 {player_data['name']} has finished with {rank_text} rank!", "success")

        last_card_val = played_cards[-1].get('joker_value', played_cards[-1]['value'])
        if last_card_val == 'ace':
            game_state['table'] = []
            for p_id_loop in game_state['players']:
                game_state['players'][p_id_loop]['skipped'] = False
            util_add_system_message(
                game_state, f"🔄 {player_data['name']} played an Ace as their last card, clearing the table!", "info")
        else:
            advance_to_next_player(game_state, save_game_state_func)
            if previous_card_on_table:
                prev_val = previous_card_on_table.get('joker_value', previous_card_on_table['value'])
                curr_val = played_cards[0].get('joker_value', played_cards[0]['value'])
                if prev_val == curr_val:
                    next_player = util_get_player_by_position(game_state, game_state['current_player_index'])
                    if next_player:
                        util_add_system_message(
                            game_state, f"⏭️ {next_player['name']} is skipped due to matching card values!", "warning")
                    advance_to_next_player(game_state, save_game_state_func)
        save_game_state_func()
        return {'success': True, 'refresh': True}

    last_card_val = played_cards[-1].get('joker_value', played_cards[-1]['value'])
    if last_card_val == 'ace':
        game_state['table'] = []
        action_msg = f"{player_data['name']} played a Joker as Ace" if played_cards[-1]['value'] == '2' else f"{player_data['name']} played an Ace"
        game_state['last_action'] = f"{action_msg}, cleared the table, and plays again!"
        util_add_system_message(game_state, f"🔄 {action_msg}, clearing the table and getting another turn!", "info")
        for p_id_loop in game_state['players']:
            game_state['players'][p_id_loop]['skipped'] = False
        game_state['required_cards_to_play'] = 1
        game_state['turn_start_time'] = time.time()
        save_game_state_func()
        return {'success': True, 'refresh': True}

    card_value = played_cards[0].get('joker_value', played_cards[0]['value'])
    card_suit = played_cards[0]['suit']
    is_joker = played_cards[0]['value'] == '2'
    num_played = len(played_cards)

    if is_joker:
        msg = f"{player_data['name']} played {num_played} Jokers as {card_value}s" if num_played > 1 else f"{player_data['name']} played a Joker as {card_value} of {card_suit}"
        util_add_system_message(game_state, f"🃏 {msg}!", "info")
    else:
        msg = f"{player_data['name']} played {num_played} {card_value}s" if num_played > 1 else f"{player_data['name']} played {card_value} of {card_suit}"
        util_add_system_message(game_state, f"🎮 {msg}", "info" if card_value in [
            'jack', 'queen', 'king', '10'] or num_played > 1 else "default")  # More specific info for high cards/multiples

    current_action_message = msg
    skip_triggered_by_match = False
    if previous_card_on_table:
        prev_val = previous_card_on_table.get('joker_value', previous_card_on_table['value'])
        if prev_val == card_value:
            current_action_message += f". This matches the previous card ({prev_val}), so the next player is skipped!"
            skip_triggered_by_match = True

    if not skip_triggered_by_match:
        current_action_message += "!" if is_joker else "."

    game_state['last_action'] = current_action_message
    advance_to_next_player(game_state, save_game_state_func)
    if skip_triggered_by_match:
        skipped_player = util_get_player_by_position(game_state, game_state['current_player_index'])
        if skipped_player:
            # Instead of marking the player as skipped, we'll just add a message and advance to the next player
            # This way they're only skipped for this round but not marked as "skipped" in their player data
            util_add_system_message(
                game_state, f"⏭️ {skipped_player['name']} is skipped due to matching card values!", "warning")
            # Store the skipped player's position in the game state to trigger animation in the frontend
            game_state['last_skipped_position'] = game_state['current_player_index']
            # Update the last action message to ensure it's detected by the frontend
            game_state['last_action'] = f"{current_action_message} {skipped_player['name']} is skipped due to matching card values!"
        advance_to_next_player(game_state, save_game_state_func)
        save_game_state_func()  # Save game state after skipping to ensure last_skipped_position is persisted

    save_game_state_func()
    return {'success': True, 'refresh': True, 'required_cards_to_play': game_state['required_cards_to_play']}


def skip_turn_logic(game_state, player_id, save_game_state_func):
    player_data = game_state['players'][player_id]
    if game_state['current_player_index'] != player_data['position']:
        return {'success': False, 'error': 'Not your turn'}
    if player_data['skipped']:
        return {'success': False, 'error': 'You have already skipped your turn'}

    player_data['skipped'] = True
    game_state['last_action'] = f"{player_data['name']} skipped their turn"
    util_add_system_message(game_state, f"⏩ {player_data['name']} skipped their turn", "warning")

    # Store the current player position to trigger skip animation
    game_state['last_skipped_position'] = player_data['position']

    all_active_skipped = all(p['skipped'] or p['rank']
                             is not None for p in game_state['players'].values() if p['rank'] is None)

    # ensure there are active players
    if all_active_skipped and any(p['rank'] is None for p in game_state['players'].values()):
        game_state['table'] = []
        game_state['last_action'] = "All active players skipped. Table cleared!"
        util_add_system_message(
            game_state, "🔄 All active players skipped! Table has been cleared for a new round.", "info")
        for p_data_loop in game_state['players'].values():
            if p_data_loop['rank'] is None:
                p_data_loop['skipped'] = False
        game_state['last_card_player_position'] = None
        game_state['last_table_length'] = 0
        game_state['required_cards_to_play'] = 1  # Reset for new round

    advance_to_next_player(game_state, save_game_state_func)
    save_game_state_func()
    return {'success': True, 'refresh': True, 'required_cards_to_play': game_state['required_cards_to_play']}


def advance_to_next_player(game_state, save_game_state_func):
    num_active_players = sum(1 for p in game_state['players'].values() if p['rank'] is None)
    if num_active_players <= 1 and any(p['rank'] is None for p in game_state['players'].values()):
        # If only one player remains or game is about to end, don't advance further in some cases.
        # This helps prevent infinite loops if logic for game end is slightly off.
        # Check if game should be over.
        if not game_state['game_over'] and len(game_state['rankings']) >= len(game_state['current_game_players']) - 1:
            # This will be handled by play_card normally, but as a safeguard:
            remaining_players = [pid for pid in game_state['current_game_players'] if pid not in game_state['rankings']]
            if len(remaining_players) <= 1:
                game_state['game_over'] = True
                # util_assign_automatic_roles(game_state, save_game_state_func) # Already called in play_card
                util_add_system_message(game_state, "🏁 Game appears to be over by player count.", "info")
                save_game_state_func()
        return  # Don't advance if only one or zero active players are left

    position_order = [0, 2, 3, 1, 4, 6, 7, 5, 8, 9, 10, 11]
    player_current_positions = {p['position']
                                for p_id, p in game_state['players'].items() if p_id in game_state['current_game_players']}
    active_positions = [pos for pos in position_order if pos in player_current_positions]
    active_positions.sort()  # Sort numerically for correct turn order
    if not active_positions:
        return  # No active players

    try:
        current_position_idx = active_positions.index(game_state['current_player_index'])
    except ValueError:
        current_position_idx = 0  # Default to first if not found
        if active_positions:
            game_state['current_player_index'] = active_positions[0]

    for _ in range(len(active_positions) * 2):
        current_position_idx = (current_position_idx + 1) % len(active_positions)
        next_player_pos = active_positions[current_position_idx]
        current_player_data = util_get_player_by_position(game_state, next_player_pos)  # Use util

        if current_player_data and not current_player_data['skipped'] and current_player_data['rank'] is None:
            game_state['current_player_index'] = next_player_pos
            break
    else:  # All remaining (active) players are skipped or have finished
        all_active_skipped_or_ranked = True
        for p_id in game_state['current_game_players']:
            p_data = game_state['players'][p_id]
            if p_data['rank'] is None and not p_data['skipped']:
                all_active_skipped_or_ranked = False
                break
        if all_active_skipped_or_ranked:
            for p_id in game_state['current_game_players']:
                p_data = game_state['players'][p_id]
                if p_data['rank'] is None:  # Only unskip active players
                    p_data['skipped'] = False
            # Attempt to find the next player again (could be the same if only one active player was skipped)
            # This primarily handles the case where one player was skipped, and now it's their turn again after reset.
            current_position_idx = active_positions.index(game_state['current_player_index'])  # Re-get current index
            for _ in range(len(active_positions) * 2):  # Loop again
                current_position_idx = (current_position_idx + 1) % len(active_positions)
                next_player_pos = active_positions[current_position_idx]
                current_player_data = util_get_player_by_position(game_state, next_player_pos)
                if current_player_data and not current_player_data['skipped'] and current_player_data['rank'] is None:
                    game_state['current_player_index'] = next_player_pos
                    break  # Found next player

    game_state['turn_start_time'] = time.time()

    if (
        game_state['table'] and
        game_state.get('last_card_player_position') is not None and
        game_state['current_player_index'] == game_state.get('last_card_player_position') and
        len(game_state['table']) == game_state.get('last_table_length', 0)
    ):
        game_state['table'] = []
        game_state['last_action'] = "Round returned to the player who placed the last card. Table cleared! Same player starts."
        util_add_system_message(
            game_state, "🔄 No one played after the last card. Table cleared and the same player starts the new round!", "info")
        for p_data_loop in game_state['players'].values():
            if p_data_loop['rank'] is None:
                p_data_loop['skipped'] = False
        game_state['last_card_player_position'] = None
        game_state['last_table_length'] = 0
        game_state['required_cards_to_play'] = 1  # Reset for new round
        save_game_state_func()
        return

    all_active_skipped_now = True
    num_active_players_check = 0
    for p_data_loop in game_state['players'].values():
        if p_data_loop['rank'] is None:
            num_active_players_check += 1
            if not p_data_loop['skipped']:
                all_active_skipped_now = False
                break

    if all_active_skipped_now and num_active_players_check > 0:
        game_state['table'] = []
        game_state['last_action'] = "All active players skipped. Table cleared!"
        util_add_system_message(
            game_state, "🔄 All active players skipped! Table has been cleared for a new round.", "info")
        for p_data_loop in game_state['players'].values():
            if p_data_loop['rank'] is None:
                p_data_loop['skipped'] = False
        game_state['last_card_player_position'] = None
        game_state['last_table_length'] = 0
        game_state['required_cards_to_play'] = 1  # Reset for new round
        save_game_state_func()


def reset_game_logic(game_state, save_game_state_func):
    game_state['table'] = []
    game_state['game_over'] = False
    game_state['winner'] = None
    game_state['required_cards_to_play'] = 1
    game_state['rankings'] = []
    game_state['card_exchange'].update({
        'active': False, 'president_id': None, 'culo_id': None, 'vice_president_id': None, 'vice_culo_id': None,
        'president_cards_to_receive': [], 'president_cards_to_give': [], 'vice_president_card_to_receive': None,
        'vice_president_card_to_give': None, 'president_exchange_completed': False, 'vice_exchange_completed': False,
        'completed': False, 'current_exchange': 'president', 'phase': 'receive'
    })
    for player_id in game_state['players']:
        game_state['players'][player_id]['hand'] = []
        game_state['players'][player_id]['skipped'] = False
        game_state['players'][player_id]['rank'] = None

    start_game(game_state, save_game_state_func)  # Call the action start_game
    game_state['last_action'] = "Game has been reset by the host"
    host_name = game_state['players'][game_state['host_player_id']]['name']
    util_add_system_message(game_state, f"🔄 {host_name} (host) has reset the game! Starting a new game...", "info")
    util_add_system_message(game_state, "------------------------", "divider")
    save_game_state_func()
    return {'success': True, 'refresh': True}


def exchange_card_logic(game_state, player_id, card_index, phase, exchange_type, save_game_state_func):
    exchange_state = game_state['card_exchange']
    if not exchange_state['active']:
        return {'success': False, 'error': 'Card exchange is not active'}
    if card_index is None:
        return {'success': False, 'error': 'No card index provided'}

    current_exchange_type = exchange_type or game_state['card_exchange']['current_exchange']

    if current_exchange_type == 'president':
        if player_id != game_state['card_exchange']['president_id']:
            return {'success': False, 'error': 'Only the President can select cards for this exchange'}
        president_data = game_state['players'][game_state['card_exchange']['president_id']]
        culo_data = game_state['players'][game_state['card_exchange']['culo_id']]

        if phase == 'receive':
            if not (0 <= card_index < len(culo_data['hand'])):
                return {'success': False, 'error': 'Invalid card index for Culo\'s hand'}
            game_state['card_exchange']['president_cards_to_receive'].append(card_index)
            if len(game_state['card_exchange']['president_cards_to_receive']) >= 2:
                game_state['card_exchange']['phase'] = 'give'
                game_state['card_exchange']['president_cards_to_receive'].sort(reverse=True)
                util_add_system_message(
                    game_state, f"👑 {president_data['name']} (President) has selected 2 cards to receive from Culo", "info")
                save_game_state_func()
                return {'success': True, 'message': 'Cards selected to receive', 'next_phase': 'give'}
            else:
                return {'success': True, 'message': 'First card selected, please select one more card',
                        'cards_selected': len(game_state['card_exchange']['president_cards_to_receive']), 'cards_needed': 2}
        elif phase == 'give':
            if not (0 <= card_index < len(president_data['hand'])):
                return {'success': False, 'error': 'Invalid card index for President\'s hand'}
            game_state['card_exchange']['president_cards_to_give'].append(card_index)
            if len(game_state['card_exchange']['president_cards_to_give']) >= 2:
                game_state['card_exchange']['president_cards_to_give'].sort(reverse=True)
                cards_to_president = [culo_data['hand'].pop(
                    idx) for idx in game_state['card_exchange']['president_cards_to_receive']]
                cards_to_culo = [president_data['hand'].pop(
                    idx) for idx in game_state['card_exchange']['president_cards_to_give']]
                president_data['hand'].extend(cards_to_president)
                culo_data['hand'].extend(cards_to_culo)
                president_data['hand'] = util_sort_cards(president_data['hand'])
                culo_data['hand'] = util_sort_cards(culo_data['hand'])
                game_state['card_exchange']['president_exchange_completed'] = True
                util_add_system_message(
                    game_state, f"🔄 Card exchange completed between {president_data['name']} (President) and {culo_data['name']} (Culo)!", "success")
                if game_state['card_exchange']['vice_president_id'] and game_state['card_exchange']['vice_culo_id']:
                    game_state['card_exchange']['current_exchange'] = 'vice'
                    game_state['card_exchange']['phase'] = 'receive'
                    util_add_system_message(
                        game_state, f"🔄 Now Vice-President and Vice-Culo will exchange 1 card each.", "info")
                else:
                    game_state['card_exchange']['completed'] = True
                    # Game begins message
                    util_add_system_message(
                        game_state, f"🎮 All card exchanges completed! The game will now begin.", "success")
                save_game_state_func()
                return {'success': True, 'message': 'President-Culo card exchange completed', 'next_exchange': game_state['card_exchange']['current_exchange']}
            else:
                return {'success': True, 'message': 'First card selected, please select one more card',
                        'cards_selected': len(game_state['card_exchange']['president_cards_to_give']), 'cards_needed': 2}

    elif current_exchange_type == 'vice':
        if player_id != game_state['card_exchange']['vice_president_id']:
            return {'success': False, 'error': 'Only the Vice-President can select cards for this exchange'}
        vice_president_data = game_state['players'][game_state['card_exchange']['vice_president_id']]
        vice_culo_data = game_state['players'][game_state['card_exchange']['vice_culo_id']]
        if phase == 'receive':
            if not (0 <= card_index < len(vice_culo_data['hand'])):
                return {'success': False, 'error': 'Invalid card index for Vice-Culo\'s hand'}
            game_state['card_exchange']['vice_president_card_to_receive'] = card_index
            game_state['card_exchange']['phase'] = 'give'
            util_add_system_message(
                game_state, f"🥈 {vice_president_data['name']} (Vice-President) has selected a card to receive from Vice-Culo", "info")
            save_game_state_func()
            return {'success': True, 'message': 'Card selected to receive', 'next_phase': 'give'}
        elif phase == 'give':
            if not (0 <= card_index < len(vice_president_data['hand'])):
                return {'success': False, 'error': 'Invalid card index for Vice-President\'s hand'}
            game_state['card_exchange']['vice_president_card_to_give'] = card_index
            vp_give_idx = game_state['card_exchange']['vice_president_card_to_give']
            # This is the index in VC's hand
            vc_give_idx = game_state['card_exchange']['vice_president_card_to_receive']

            # Ensure indices are valid before popping
            if not (0 <= vp_give_idx < len(vice_president_data['hand'])) or not (0 <= vc_give_idx < len(vice_culo_data['hand'])):
                return {'success': False, 'error': 'Invalid card index during vice exchange execution.'}

            vp_card_to_give = vice_president_data['hand'].pop(vp_give_idx)
            vc_card_to_give = vice_culo_data['hand'].pop(vc_give_idx)

            vice_president_data['hand'].append(vc_card_to_give)
            vice_culo_data['hand'].append(vp_card_to_give)

            vice_president_data['hand'] = util_sort_cards(vice_president_data['hand'])
            vice_culo_data['hand'] = util_sort_cards(vice_culo_data['hand'])
            game_state['card_exchange']['vice_exchange_completed'] = True
            game_state['card_exchange']['completed'] = True
            util_add_system_message(
                game_state, f"🔄 Card exchange completed between {vice_president_data['name']} (Vice-President) and {vice_culo_data['name']} (Vice-Culo)!", "success")
            util_add_system_message(game_state, f"🎮 All card exchanges completed! The game will now begin.", "success")
            save_game_state_func()
            return {'success': True, 'message': 'Vice-President-Vice-Culo card exchange completed'}
    else:
        return {'success': False, 'error': 'Invalid exchange type'}
