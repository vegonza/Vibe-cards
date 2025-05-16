import uuid
from culo_game.config.config import CARD_VALUES


def sort_cards(cards):
    """Sort cards by suit and value

    Sorts in the following order:
    1. By value (2, 3, 4, ..., Jack, Queen, King, Ace)
    2. By suit (hearts, diamonds, clubs, spades)

    Args:
        cards: List of card dictionaries to sort

    Returns:
        Sorted list of cards
    """
    # Define suit order (hearts, diamonds, clubs, spades)
    suit_order = {'hearts': 0, 'diamonds': 1, 'clubs': 2, 'spades': 3}

    # Sort by numeric value first, then by suit
    return sorted(cards, key=lambda card: (card['numeric_value'], suit_order[card['suit']]))


def validate_card_play(selected_cards, top_card, joker_value=None):
    """Validate if the selected cards can be played according to game rules

    Args:
        selected_cards: List of card dictionaries to play
        top_card: The top card on the table (or None if table is empty)
        joker_value: Optional value for jokers

    Returns:
        (bool, str): (is_valid, error_message)
    """
    # Rule 1: If table is empty, any card(s) can be played
    if not top_card:
        return True, ""

    # For multiple cards, validate they all have the same effective value
    if len(selected_cards) > 1:
        reference_value = None
        is_playing_only_jokers = True

        # Determine the reference value for the play
        for card_in_hand in selected_cards:
            if card_in_hand['value'] != '2':
                reference_value = card_in_hand['value']
                is_playing_only_jokers = False
                break

        if is_playing_only_jokers:
            if joker_value:  # All selected are jokers, and a value is specified
                reference_value = joker_value
            else:  # All selected are jokers, but no specific value given (e.g. played as '2's)
                reference_value = '2'
        elif not reference_value:  # Should only happen if selected_cards was empty
            return False, "Error determining reference value for multi-card play."

        # Now, validate that all selected cards effectively match this reference_value
        for card_in_hand in selected_cards:
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

            if effective_value != reference_value:
                return False, "Selected cards must have the same value (considering jokers)."

    # Determine the effective value of the play for comparison with top card
    effective_play_value_for_comparison = None
    if joker_value:  # Player explicitly chose a value for jokers
        effective_play_value_for_comparison = CARD_VALUES.get(joker_value)
    elif len(selected_cards) > 0:
        # If no explicit joker_value, but we are playing non-jokers, use their value.
        # Or if playing only jokers (as 2s), use the value of '2'.
        first_card = selected_cards[0]
        if first_card['value'] != '2':
            effective_play_value_for_comparison = first_card['numeric_value']
        elif not any(c['value'] != '2' for c in selected_cards):  # All are 2s, no other cards
            effective_play_value_for_comparison = CARD_VALUES['2']  # They are played as 2s
        else:  # Mixed play (e.g. K and 2)
            # Find the non-joker card to get the reference value
            non_joker_in_selection = next((c['value'] for c in selected_cards if c['value'] != '2'), None)
            if non_joker_in_selection:
                effective_play_value_for_comparison = CARD_VALUES.get(non_joker_in_selection)
            else:  # Should not happen if prior validation is correct
                effective_play_value_for_comparison = CARD_VALUES['2']

    # Rule 2: "2 as Joker" rule - 2s can be played on anything
    if all(card['value'] == '2' for card in selected_cards) and not joker_value:
        return True, ""

    # Rule 3: Regular rule - cards must be equal or higher value than top card
    if effective_play_value_for_comparison is not None and effective_play_value_for_comparison >= top_card['numeric_value']:
        return True, ""

    # If we get here, the play is invalid
    error_detail = f"Top card: {top_card['value']}. Your play (effective): {effective_play_value_for_comparison}. Joker value: {joker_value}."
    return False, f"Invalid card(s). You must play card(s) with equal or higher value, or 2s. {error_detail}"


def prepare_cards_for_play(card_indices, player_hand, joker_value=None):
    """Prepare cards from player's hand for playing

    Args:
        card_indices: List of indices of cards to play
        player_hand: Player's current hand
        joker_value: Optional value for jokers

    Returns:
        List of card dictionaries ready to be played
    """
    # Sort indices in descending order to avoid shifting issues when removing
    card_indices.sort(reverse=True)

    # Get the cards to be played
    played_cards = []
    for idx in card_indices:
        played_card = player_hand[idx].copy()  # Make a copy to avoid modifying the original
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

    return played_cards
