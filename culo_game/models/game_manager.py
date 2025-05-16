import random
import time
from culo_game.models.game_state import GameState
from culo_game.models.card import sort_cards


class GameManager:
    """Game manager class to handle game logic"""

    @staticmethod
    def start_game():
        """Start the game by dealing cards to all players"""
        game_state = GameState()

        # Create and shuffle the deck
        deck = game_state.create_deck()
        random.shuffle(deck)

        # Count the number of players
        num_players = len(game_state.data['players'])

        # Calculate how many cards each player should get
        # We want to distribute the entire deck evenly
        cards_per_player = len(deck) // num_players

        # Sort players by position to ensure consistent dealing
        sorted_players = sorted(game_state.data['players'].items(), key=lambda x: x[1]['position'])

        # Reset rankings for new game
        game_state.data['rankings'] = []

        # Store current players in the game
        game_state.data['current_game_players'] = [player_id for player_id, _ in sorted_players]

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
        game_state.data['started'] = True

        # Define the clockwise order of positions
        position_order = [0, 2, 3, 1, 4, 6, 7, 5, 8, 9, 10, 11]

        # Get the positions of players in the game, sorted by the clockwise order
        player_positions = [player['position'] for player in game_state.data['players'].values()]

        # Find the first position in our order that has a player
        first_player_position = next((pos for pos in position_order if pos in player_positions), 0)

        # Set the current player to the first player in the clockwise order
        game_state.data['current_player_index'] = first_player_position

        game_state.data['table'] = []
        game_state.data['last_card_played'] = None
        game_state.data['last_action'] = None
        game_state.data['chat_messages'] = []  # Clear chat on new game
        game_state.data['turn_start_time'] = time.time()  # Initialize turn start time

        # Check if we need to initiate card exchange (president and culo roles exist)
        GameManager._setup_card_exchange()

        # Add system message for game start
        player_names = [player['name'] for player in game_state.data['players'].values()]
        game_state.add_system_message(f"🎮 Game started with players: {', '.join(player_names)}", "success")

        # Save game state after starting the game
        game_state.save_state()

    @staticmethod
    def _setup_card_exchange():
        """Setup card exchange if president and culo roles exist"""
        game_state = GameState()

        president_id = None
        culo_id = None
        vice_president_id = None
        vice_culo_id = None

        for player_id, player_data in game_state.data['players'].items():
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
            game_state.data['card_exchange'] = {
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
            game_state.add_system_message(
                f"🔄 Card exchange is now active! President takes 2 cards from Culo and gives 2 cards back.", "info")

            if vice_president_id and vice_culo_id:
                game_state.add_system_message(
                    f"🔄 Vice-President and Vice-Culo will exchange 1 card each after the President's exchange.", "info")
        else:
            # No card exchange needed
            game_state.data['card_exchange'] = {
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

    @staticmethod
    def redistribute_cards():
        """Redistribute all cards when a new player joins"""
        game_state = GameState()

        # Get the new player (the one without cards)
        new_player_id = None
        new_player_data = None

        for player_id, player_data in game_state.data['players'].items():
            if len(player_data['hand']) == 0 and player_data['rank'] is None:
                new_player_id = player_id
                new_player_data = player_data
                break

        if not new_player_id:
            # No new player found, this shouldn't happen
            return

        # Create a new deck for the new player
        new_player_cards = game_state.create_deck()
        random.shuffle(new_player_cards)

        # Calculate how many cards the new player should get
        # We'll give them roughly the average number of cards other players have
        total_cards = 0
        active_players = 0

        for player_id, player_data in game_state.data['players'].items():
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
        if new_player_id not in game_state.data['current_game_players']:
            game_state.data['current_game_players'].append(new_player_id)

        # Add system message
        game_state.add_system_message(
            f"🃏 {new_player_data['name']} has been dealt {len(new_player_data['hand'])} cards and joined the game in progress!", "info")

        # Save game state after redistributing cards
        game_state.save_state()

    @staticmethod
    def advance_to_next_player():
        """Move to the next player in turn order"""
        game_state = GameState()

        num_players = len(game_state.data['players'])
        previous_player_index = game_state.data['current_player_index']
        previous_table_length = len(game_state.data['table'])

        # Define the clockwise order of positions
        position_order = [0, 2, 3, 1, 4, 6, 7, 5, 8, 9, 10, 11]

        # Get active positions (positions of players in the game) in the correct clockwise order
        player_current_positions = {player['position'] for player in game_state.data['players'].values()}
        active_positions = [pos for pos in position_order if pos in player_current_positions]

        # Find the current position's index in our active positions list
        try:
            current_position_idx = active_positions.index(game_state.data['current_player_index'])
        except ValueError:
            # If current position is not found (shouldn't happen), default to the first position
            current_position_idx = 0
            if active_positions:
                game_state.data['current_player_index'] = active_positions[0]

        # Find the next player who hasn't skipped and hasn't finished (no rank)
        for _ in range(num_players * 2):  # Increased loop limit to ensure we find a valid player
            # Move to next player in the clockwise order
            current_position_idx = (current_position_idx + 1) % len(active_positions)
            game_state.data['current_player_index'] = active_positions[current_position_idx]

            # Get the current player
            current_player = None
            for player in game_state.data['players'].values():
                if player['position'] == game_state.data['current_player_index']:
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
                for player in game_state.data['players'].values():
                    if player['rank'] is None and not player['skipped']:
                        all_active_skipped = False
                        break

                # If all active players skipped, reset skip status for all players without ranks
                if all_active_skipped:
                    for player in game_state.data['players'].values():
                        if player['rank'] is None:
                            player['skipped'] = False

                    # Try again with reset skip statuses (will be handled in the next iteration)
                    continue

        # Reset turn timer for the new player
        game_state.data['turn_start_time'] = time.time()

        # --- NEW RULE: If round returns to last card player and no new card was played ---
        # Only if table is not empty (otherwise, it's already a new round)
        if (
            game_state.data['table'] and
            game_state.data.get('last_card_player_position') is not None and
            game_state.data['current_player_index'] == game_state.data.get('last_card_player_position') and
            len(game_state.data['table']) == game_state.data.get('last_table_length', 0)
        ):
            # Clear the table and let this player start
            game_state.data['table'] = []
            game_state.data['last_action'] = "Round returned to the player who placed the last card. Table cleared! Same player starts."
            game_state.add_system_message(
                "🔄 No one played after the last card. Table cleared and the same player starts the new round!", "info")
            # Reset all players' skipped status
            for player in game_state.data['players'].values():
                if player['rank'] is None:  # Only reset skip status for players still in the game
                    player['skipped'] = False
            # Reset last_card_player_position and last_table_length since table is now empty
            game_state.data['last_card_player_position'] = None
            game_state.data['last_table_length'] = 0

            # Save game state after clearing table
            game_state.save_state()
            return  # End turn advancement here

        # If all active players (those without ranks) have skipped, reset the table and skipped status
        all_active_skipped = True
        for player in game_state.data['players'].values():
            if player['rank'] is None and not player['skipped']:
                all_active_skipped = False
                break

        if all_active_skipped:
            game_state.data['table'] = []
            game_state.data['last_action'] = "All active players skipped. Table cleared!"

            # Add system message for all players skipping
            game_state.add_system_message(
                "🔄 All active players skipped! Table has been cleared for a new round.", "info")

            # Reset all active players' skipped status
            for player in game_state.data['players'].values():
                if player['rank'] is None:  # Only reset skip status for players still in the game
                    player['skipped'] = False
            # Reset last_card_player_position and last_table_length since table is now empty
            game_state.data['last_card_player_position'] = None
            game_state.data['last_table_length'] = 0

            # Save game state after clearing table due to all players skipping
            game_state.save_state()

    @staticmethod
    def assign_automatic_roles():
        """Automatically assign roles based on player finishing order"""
        game_state = GameState()

        total_players = len(game_state.data['rankings'])

        # Reset all roles to neutral first
        for player_id in game_state.data['players']:
            game_state.data['players'][player_id]['role'] = 'neutral'

        # Only assign roles if we have at least 2 players
        if total_players >= 2:
            # First player is president
            if len(game_state.data['rankings']) > 0:
                president_id = game_state.data['rankings'][0]
                game_state.data['players'][president_id]['role'] = 'president'
                president_name = game_state.data['players'][president_id]['name']
                game_state.add_system_message(f"👑 {president_name} is now the President!", "success")

            # Last player is culo
            if len(game_state.data['rankings']) > 0:
                culo_id = game_state.data['rankings'][-1]
                game_state.data['players'][culo_id]['role'] = 'culo'
                culo_name = game_state.data['players'][culo_id]['name']
                game_state.add_system_message(f"💩 {culo_name} is now the Culo!", "warning")

            # If we have at least 4 players, assign vice roles
            if total_players >= 4:
                # Second player is vice-president
                if len(game_state.data['rankings']) > 1:
                    vice_president_id = game_state.data['rankings'][1]
                    game_state.data['players'][vice_president_id]['role'] = 'vice-president'
                    vice_president_name = game_state.data['players'][vice_president_id]['name']
                    game_state.add_system_message(f"🥈 {vice_president_name} is now the Vice-President!", "success")

                # Second-to-last player is vice-culo
                if len(game_state.data['rankings']) > 2:
                    vice_culo_index = total_players - 2
                    if vice_culo_index < len(game_state.data['rankings']):
                        vice_culo_id = game_state.data['rankings'][vice_culo_index]
                        game_state.data['players'][vice_culo_id]['role'] = 'vice-culo'
                        vice_culo_name = game_state.data['players'][vice_culo_id]['name']
                        game_state.add_system_message(f"💩 {vice_culo_name} is now the Vice-Culo!", "warning")

            # Add system message about role assignment
            game_state.add_system_message(f"👥 Roles have been automatically assigned based on finishing order!", "info")

            # Save game state after roles are automatically assigned
            game_state.save_state()

    @staticmethod
    def reset_game():
        """Reset the game state for a new game"""
        game_state = GameState()

        # Clear the table and player hands
        game_state.data['table'] = []
        game_state.data['game_over'] = False
        game_state.data['winner'] = None
        game_state.data['required_cards_to_play'] = 1  # Reset to 1 card per play
        game_state.data['rankings'] = []  # Reset rankings

        # Reset card exchange state
        game_state.data['card_exchange'] = {
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

        for player_id, player_data in game_state.data['players'].items():
            player_data['hand'] = []
            player_data['skipped'] = False
            player_data['rank'] = None  # Reset rank
            # Don't reset roles - roles persist across games unless manually changed

        # Start a new game
        GameManager.start_game()

        game_state.data['last_action'] = "Game has been reset by the host"

        # Keep chat history but add a divider
        game_state.add_system_message("------------------------", "divider")

        # Save game state after reset
        game_state.save_state()
