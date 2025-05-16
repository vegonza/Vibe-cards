document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements
    const playerHand = document.getElementById('player-hand');
    const tableCards = document.querySelector('.table-cards');
    const skipTurnButton = document.getElementById('skip-turn');
    const playSelectedButton = document.getElementById('play-selected');
    const lastActionElement = document.getElementById('last-action');
    const tableCircleElement = document.querySelector('.table-circle'); // Added for animation origin

    // Host controls elements
    const hostControlsPanel = document.getElementById('host-controls');
    const hostNewGameButton = document.getElementById('host-new-game');
    const hostResetGameButton = document.getElementById('host-reset-game');
    const hostAssignRanksButton = document.getElementById('host-assign-ranks');
    const hostAssignRolesButton = document.getElementById('host-assign-roles');
    const hostChangeDeckButton = document.getElementById('host-change-deck');
    const hostKickPlayersButton = document.getElementById('host-kick-players');
    const hostStartGameButton = document.getElementById('host-start-game');

    // Role assignment modal elements
    const roleAssignmentModal = document.getElementById('role-assignment-modal');
    const roleAssignmentPlayers = document.getElementById('role-assignment-players');
    const saveRolesButton = document.getElementById('save-roles-btn');
    const cancelRolesButton = document.getElementById('cancel-roles-btn');

    // Deck size modal elements
    const deckSizeModal = document.getElementById('deck-size-modal');
    const saveDeckButton = document.getElementById('save-deck-btn');
    const cancelDeckButton = document.getElementById('cancel-deck-btn');
    const deckSizeRadios = document.querySelectorAll('input[name="deck-size"]');

    // Kick players modal elements
    const kickPlayersModal = document.getElementById('kick-players-modal');
    const kickPlayersList = document.getElementById('kick-players-list');
    const cancelKickButton = document.getElementById('cancel-kick-btn');

    // Turn timer variables
    let turnTimerInterval = null;
    let currentTurnTimeLeft = 0;
    let turnTimerDuration = 20; // Default 20 seconds

    // Track current player's name for optimistic chat updates
    let localPlayerName = "Me"; // Default fallback

    // Track if the current player is the host
    let isHost = false;

    // Track all players data
    let allPlayersData = [];

    // Track selected cards (array of card indices)
    let selectedCards = [];

    // Track the required number of cards to play (set by the server)
    let requiredCardsToPlay = 1;

    // Track current deck size
    let currentDeckSize = 1;

    // Track card exchange state
    let cardExchangeActive = false;
    let isPresident = false;
    let isCulo = false;
    let isVicePresident = false;
    let isViceCulo = false;
    let presidentCardsToReceive = [];
    let presidentCardsToGive = [];
    let vicePresidentCardToReceive = null;
    let vicePresidentCardToGive = null;
    let presidentExchangeCompleted = false;
    let viceExchangeCompleted = false;
    let exchangeCompleted = false;
    let currentExchange = 'president';
    let exchangePhase = 'receive';
    let culoHand = [];
    let viceCuloHand = [];

    // Client-side animation flags
    let dealAnimationInProgress = false;
    let hasInitialDealAnimationPlayed = false;
    const DEAL_ANIMATION_CARD_DURATION = 150; // ms per card for animation
    const DEAL_ANIMATION_STAGGER_DELAY = 75; // ms stagger for each card animation start

    // Chat elements
    const chatLog = document.getElementById('chat-log');
    const chatMessageInput = document.getElementById('chat-message-input');
    const sendMessageButton = document.getElementById('send-message-button');

    // Rules modal elements
    const rulesButton = document.getElementById('rules-button');
    const rulesModal = document.getElementById('rules-modal');
    const closeRulesButton = document.getElementById('close-rules');

    // Settings modal elements
    const settingsButton = document.getElementById('settings-button');
    const settingsModal = document.getElementById('settings-modal');
    const closeSettingsButton = document.getElementById('close-settings');
    const clearPlayerNameButton = document.getElementById('clear-player-name');

    // Create joker value selection modal
    const jokerModal = document.createElement('div');
    jokerModal.className = 'joker-modal';
    jokerModal.innerHTML = `
        <div class="joker-content">
            <h2>Choose Joker Value</h2>
            <p>Select which card value you want your joker (2) to represent:</p>
            <div class="joker-options">
                <!-- Options will be dynamically added here -->
            </div>
            <button class="cancel-joker">Cancel</button>
        </div>
    `;
    document.body.appendChild(jokerModal);

    // Create card exchange modal
    const cardExchangeModal = document.createElement('div');
    cardExchangeModal.className = 'card-exchange-modal';
    cardExchangeModal.innerHTML = `
        <div class="card-exchange-content">
            <h2 id="card-exchange-title">Select a Card</h2>
            <div class="card-exchange-counter" id="card-exchange-counter">
                <span class="counter-icon">🃏</span>
                <span class="counter-text">0/2</span>
            </div>
            <p id="card-exchange-description">Choose a card for the exchange:</p>
            <div class="card-exchange-cards">
                <!-- Cards will be dynamically added here -->
            </div>
            <div class="card-exchange-info">
                <p id="card-exchange-status"></p>
            </div>
        </div>
    `;
    document.body.appendChild(cardExchangeModal);

    // Get joker modal elements
    const jokerOptions = jokerModal.querySelector('.joker-options');
    const cancelJokerButton = jokerModal.querySelector('.cancel-joker');

    // Get card exchange modal elements
    const cardExchangeTitle = cardExchangeModal.querySelector('#card-exchange-title');
    const cardExchangeDescription = cardExchangeModal.querySelector('#card-exchange-description');
    const cardExchangeCards = cardExchangeModal.querySelector('.card-exchange-cards');
    const cardExchangeStatus = cardExchangeModal.querySelector('#card-exchange-status');

    // Joker selection state
    let jokerSelectionActive = false;
    let jokerCardIndex = null;
    let jokerCardIndices = [];

    // Track if the current player has finished (has a rank)
    let playerHasFinished = false;

    // Rules modal functionality
    if (rulesButton && rulesModal && closeRulesButton) {
        rulesButton.addEventListener('click', () => {
            rulesModal.style.display = 'flex';
        });

        closeRulesButton.addEventListener('click', () => {
            rulesModal.style.display = 'none';
        });

        // Close modal when clicking outside of it
        rulesModal.addEventListener('click', (event) => {
            if (event.target === rulesModal) {
                rulesModal.style.display = 'none';
            }
        });

        // Close modal with escape key
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && rulesModal.style.display === 'flex') {
                rulesModal.style.display = 'none';
            }
        });
    }

    // Settings modal functionality
    if (settingsButton && settingsModal && closeSettingsButton) {
        settingsButton.addEventListener('click', () => {
            settingsModal.style.display = 'flex';
        });

        closeSettingsButton.addEventListener('click', () => {
            settingsModal.style.display = 'none';
        });

        // Close modal when clicking outside of it
        settingsModal.addEventListener('click', (event) => {
            if (event.target === settingsModal) {
                settingsModal.style.display = 'none';
            }
        });

        // Close modal with escape key
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && settingsModal.style.display === 'flex') {
                settingsModal.style.display = 'none';
            }
        });

        // Clear player name from localStorage
        if (clearPlayerNameButton) {
            clearPlayerNameButton.addEventListener('click', () => {
                if (localStorage.getItem('culoPlayerName')) {
                    localStorage.removeItem('culoPlayerName');
                    alert('Your saved player name has been cleared.');
                } else {
                    alert('No saved player name found.');
                }
            });
        }
    }

    // Helper function to create a chat message DOM element
    function createChatMessageElement(msg) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('chat-message');

        if (msg.id) { // Server messages and optimistic local messages will have an ID
            messageElement.dataset.messageId = msg.id;
        }

        const isSystem = msg.sender === 'System';
        if (isSystem) {
            messageElement.classList.add('system');
            if (msg.type) {
                messageElement.classList.add(msg.type);
            }
            if (msg.type === 'divider') {
                messageElement.textContent = msg.text;
                return messageElement; // Return early for divider
            }

            // Create a more compact system message
            const iconMap = {
                'info': 'ℹ️',
                'success': '✅',
                'warning': '⚠️',
                'error': '❌',
            };

            const icon = iconMap[msg.type] || '🔄';

            // For system messages, use a more compact format
            const textElement = document.createElement('span');
            textElement.classList.add('text');
            textElement.innerHTML = `${icon} ${msg.text}`;

            const timestampElement = document.createElement('span');
            timestampElement.classList.add('timestamp');
            timestampElement.textContent = `(${msg.timestamp})`;

            messageElement.appendChild(textElement);
            messageElement.appendChild(timestampElement);

            return messageElement;
        }

        const senderElement = document.createElement('span');
        senderElement.classList.add('sender');
        senderElement.textContent = msg.sender;

        const textElement = document.createElement('span');
        textElement.classList.add('text');
        textElement.innerHTML = isSystem ? ` ${msg.text}` : `: ${msg.text}`; // XSS vulnerability introduced here

        const timestampElement = document.createElement('span');
        timestampElement.classList.add('timestamp');
        timestampElement.textContent = `(${msg.timestamp})`;

        messageElement.appendChild(senderElement);
        messageElement.appendChild(textElement);
        messageElement.appendChild(timestampElement);
        return messageElement;
    }

    // Helper function to append a message (optimistic or server)
    function appendMessageToChatLog(msg) {
        if (!chatLog) return;
        const messageElement = createChatMessageElement(msg);
        chatLog.appendChild(messageElement);
        chatLog.scrollTop = chatLog.scrollHeight; // Scroll to bottom
    }

    // Add event listeners to cards in player's hand
    function addCardListeners() {
        const cards = playerHand.querySelectorAll('.card:not(.disabled)');
        cards.forEach(card => {
            card.addEventListener('click', handleCardClick);
        });
    }

    // Track the last animated card's ID to avoid looping animation
    let lastAnimatedCardId = null;

    // Handle card click event - now toggles selection instead of playing immediately
    function handleCardClick(event) {
        const card = event.currentTarget;
        const cardIndex = parseInt(card.dataset.index);

        if (card.classList.contains('disabled') || playerHasFinished) {
            return; // Do nothing for disabled cards or if player has finished
        }

        // Determine if the table is currently empty
        const isTableEmpty = tableCards.children.length === 0;

        // Check if this is a joker (2) card
        const isJoker = card.dataset.value === '2';

        // Auto-play only in single-card rounds when table is not empty
        if (requiredCardsToPlay === 1 && !isTableEmpty) {
            if (isJoker) {
                // For jokers, show the value selection modal
                showJokerValueSelection([cardIndex]);
            } else {
                playSingleCard(cardIndex);
            }
        } else {
            // Toggle selection for multiple card play mode or initial selection
            if (card.classList.contains('selected')) {
                // Remove from selection
                card.classList.remove('selected');
                selectedCards = selectedCards.filter(idx => idx !== cardIndex);
            } else {
                // Add to selection
                card.classList.add('selected');
                selectedCards.push(cardIndex);
            }
            // Update play selected button state
            updatePlaySelectedButtonState(playerHasFinished);
        }
    }

    // Update the play selected button state based on selection
    function updatePlaySelectedButtonState(playerHasFinished = false) {
        if (!playSelectedButton) return;

        // If player has finished, disable and hide the button
        if (playerHasFinished) {
            playSelectedButton.style.display = 'none';
            return;
        }

        // Determine if the table is currently empty
        const isTableEmpty = tableCards.children.length === 0;

        // In single-card rounds with non-empty table, hide the button (auto-play mode)
        if (requiredCardsToPlay === 1 && !isTableEmpty) {
            playSelectedButton.style.display = 'none';
            // Clear any selections if present
            if (selectedCards.length > 0) {
                selectedCards.forEach(idx => {
                    const cardElement = playerHand.querySelector(`.card[data-index="${idx}"]`);
                    if (cardElement) cardElement.classList.remove('selected');
                });
                selectedCards = [];
            }
        } else {
            // Show the play button in initial or multi-card rounds
            playSelectedButton.style.display = 'block';
            // Determine button disabled state
            if (isTableEmpty) {
                // Initial round: any number of selected cards allowed
                playSelectedButton.disabled = selectedCards.length === 0;
            } else {
                // Subsequent multi-card rounds: must match required count
                playSelectedButton.disabled = (selectedCards.length === 0 || selectedCards.length !== requiredCardsToPlay);
            }
            // Update button text
            if (isTableEmpty) {
                if (selectedCards.length > 1) {
                    playSelectedButton.textContent = `Play ${selectedCards.length} Cards`;
                } else {
                    playSelectedButton.textContent = 'Play Selected';
                }
            } else {
                // Multi-card round text
                playSelectedButton.textContent = `Play Selected (${selectedCards.length}/${requiredCardsToPlay})`;
            }
        }
    }

    // Play a single card directly
    function playSingleCard(cardIndex, jokerValue = null) {
        const cardElement = playerHand.querySelector(`.card[data-index="${cardIndex}"]`);
        if (!cardElement || cardElement.classList.contains('disabled')) {
            console.warn("Attempted to play a disabled or non-existent card.");
            return;
        }

        // Visually indicate the card is being played (optional, e.g., temp disable)
        cardElement.classList.add('disabled'); // Temporarily disable to prevent multi-clicks

        const requestData = { card_indices: [cardIndex] };

        // Add joker value if provided
        if (jokerValue) {
            requestData.joker_value = jokerValue;
        }

        fetch('/play_card', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData),
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (data.refresh) {
                        // requiredCardsToPlay might change, so update it
                        if (data.required_cards_to_play !== undefined) {
                            requiredCardsToPlay = data.required_cards_to_play;
                        }
                        fetchGameState(); // Refresh game state
                    }
                } else {
                    // Re-enable the card if there was an error
                    cardElement.classList.remove('disabled');
                    console.error('Error playing single card:', data.error);
                    alert(data.error || 'Failed to play the card.');
                }
            })
            .catch(error => {
                // Re-enable the card on network error
                cardElement.classList.remove('disabled');
                console.error('Error:', error);
                alert('An error occurred while trying to play the card.');
            });
    }

    // Play selected cards
    function playSelectedCards(jokerValue = null) {
        if (selectedCards.length === 0) return;

        // Disable the button immediately to prevent double-clicks
        playSelectedButton.disabled = true;

        // Disable the selected cards visually
        selectedCards.forEach(cardIndex => {
            const cardElement = document.querySelector(`.card[data-index="${cardIndex}"]`);
            if (cardElement) {
                cardElement.classList.add('disabled');
            }
        });

        // Get all selected cards' values
        const selectedCardElements = selectedCards.map(index => {
            const cardElement = document.querySelector(`.card[data-index="${index}"]`);
            return {
                element: cardElement,
                value: cardElement ? cardElement.dataset.value : null
            };
        });

        // Check if we have a mix of jokers and non-jokers
        const jokerCards = selectedCardElements.filter(card => card.value === '2');
        const nonJokerCards = selectedCardElements.filter(card => card.value !== '2');

        // If we have both jokers and non-jokers, use the non-joker value
        if (jokerCards.length > 0 && nonJokerCards.length > 0) {
            jokerValue = nonJokerCards[0].value;
        }
        // If all cards are jokers and no joker value is set, show the joker value selection
        else if (jokerCards.length === selectedCardElements.length && !jokerValue) {
            // Re-enable the cards and button
            selectedCards.forEach(cardIndex => {
                const cardElement = document.querySelector(`.card[data-index="${cardIndex}"]`);
                if (cardElement) {
                    cardElement.classList.remove('disabled');
                }
            });
            playSelectedButton.disabled = false;

            // Show joker value selection
            showJokerValueSelection(selectedCards);
            return;
        }

        // Prepare request data
        const requestData = { card_indices: selectedCards };

        // Add joker value if provided
        if (jokerValue) {
            requestData.joker_value = jokerValue;
        }

        // Send request to play the selected cards
        fetch('/play_card', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData),
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (data.refresh) {
                        // Store the required cards count if provided
                        if (data.required_cards_to_play !== undefined) {
                            requiredCardsToPlay = data.required_cards_to_play;
                        }

                        // Clear selection before refresh
                        selectedCards = [];

                        // Refresh the game state
                        fetchGameState();
                    }
                } else {
                    // Re-enable the cards and button if there was an error
                    selectedCards.forEach(cardIndex => {
                        const cardElement = document.querySelector(`.card[data-index="${cardIndex}"]`);
                        if (cardElement) {
                            cardElement.classList.remove('disabled');
                        }
                    });
                    playSelectedButton.disabled = false;
                    console.error('Error playing cards:', data.error);

                    // Show error message to user
                    alert(data.error || 'Failed to play selected cards');
                }
            })
            .catch(error => {
                // Re-enable the cards and button if there was an error
                selectedCards.forEach(cardIndex => {
                    const cardElement = document.querySelector(`.card[data-index="${cardIndex}"]`);
                    if (cardElement) {
                        cardElement.classList.remove('disabled');
                    }
                });
                playSelectedButton.disabled = false;
                console.error('Error:', error);
            });
    }

    // Show joker value selection modal
    function showJokerValueSelection(cardIndices) {
        // Store the joker card indices
        jokerCardIndices = cardIndices;
        jokerSelectionActive = true;

        // Clear previous options
        jokerOptions.innerHTML = '';

        // Get the top card on the table (if any)
        let topCard = null;
        if (tableCards.children.length > 0) {
            const lastCardElement = tableCards.lastChild;
            topCard = {
                value: lastCardElement.dataset.value,
                suit: lastCardElement.dataset.suit
            };
        }

        // Add card value options (3 through Ace)
        const cardValues = ['3', '4', '5', '6', '7', '8', '9', '10', 'jack', 'queen', 'king', 'ace'];

        cardValues.forEach(value => {
            const option = document.createElement('div');
            option.className = 'joker-option';

            // Display value (convert face cards to first letter uppercase)
            let displayValue = value;
            if (['jack', 'queen', 'king', 'ace'].includes(value)) {
                displayValue = value[0].toUpperCase();
            }

            option.innerHTML = `
                <div class="mini-card">
                    <div class="mini-card-value">${displayValue}</div>
                </div>
                <div class="option-label">${value.charAt(0).toUpperCase() + value.slice(1)}</div>
            `;

            // Add click event
            option.addEventListener('click', () => {
                jokerModal.style.display = 'none';
                jokerSelectionActive = false;

                // Play the joker with the selected value
                if (jokerCardIndices.length === 1 && requiredCardsToPlay === 1 && tableCards.children.length > 0) {
                    playSingleCard(jokerCardIndices[0], value);
                } else {
                    playSelectedCards(value);
                }
            });

            jokerOptions.appendChild(option);
        });

        // Show the modal
        jokerModal.style.display = 'flex';
    }

    // Cancel joker selection
    cancelJokerButton.addEventListener('click', () => {
        jokerModal.style.display = 'none';
        jokerSelectionActive = false;
        jokerCardIndices = [];
    });

    // Close joker modal when clicking outside
    jokerModal.addEventListener('click', (event) => {
        if (event.target === jokerModal) {
            jokerModal.style.display = 'none';
            jokerSelectionActive = false;
            jokerCardIndices = [];
        }
    });

    // Skip turn event
    skipTurnButton.addEventListener('click', () => {
        // Disable the button immediately to prevent double-clicks
        skipTurnButton.disabled = true;

        // Show skip animation immediately on the current player
        const currentPlayerElement = document.querySelector('.player-avatar.current-turn');
        if (currentPlayerElement) {
            const playerPosition = currentPlayerElement.closest('.player-position')?.classList[1]?.split('-')[1];
            if (playerPosition) {
                console.log("Current player position for skip:", playerPosition);
                showSkipAnimation(playerPosition);
            }
        }

        fetch('/skip_turn', {
            method: 'POST',
        })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.refresh) {
                    fetchGameState();
                } else {
                    // Re-enable the button if there was an error
                    skipTurnButton.disabled = false;
                    console.error('Error skipping turn:', data.error);
                }
            })
            .catch(error => {
                // Re-enable the button if there was an error
                skipTurnButton.disabled = false;
                console.error('Error:', error);
            });
    });

    // Reset game event is now handled in the host controls

    // Function to show a notification overlay and redirect after delay
    function showNotificationAndRedirect(title, message, color, delay = 3000) {
        // Create a notification overlay
        const overlay = document.createElement('div');
        overlay.style.position = 'fixed';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
        overlay.style.display = 'flex';
        overlay.style.justifyContent = 'center';
        overlay.style.alignItems = 'center';
        overlay.style.zIndex = '9999';

        const messageBox = document.createElement('div');
        messageBox.style.backgroundColor = '#34495e';
        messageBox.style.color = '#ecf0f1';
        messageBox.style.padding = '20px';
        messageBox.style.borderRadius = '10px';
        messageBox.style.maxWidth = '400px';
        messageBox.style.textAlign = 'center';
        messageBox.innerHTML = `
            <h3 style="color: ${color}; margin-top: 0;">${title}</h3>
            <p>${message}</p>
            <p>You'll be redirected to the join page in a moment...</p>
        `;

        overlay.appendChild(messageBox);
        document.body.appendChild(overlay);

        // Redirect after a short delay so the user can read the message
        setTimeout(() => {
            window.location.href = '/';
        }, delay);
    }

    // Fetch the current game state
    function fetchGameState() {
        fetch('/get_game_state')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Reset error counter on successful response
                    window.gameStateErrorCount = 0;

                    // Store the required cards count if provided
                    if (data.required_cards_to_play !== undefined) {
                        requiredCardsToPlay = data.required_cards_to_play;
                    }

                    updateGameState(data);
                } else if (data.error === 'No player ID in session' || data.error === 'Player not found') {
                    // Player ID is no longer valid (server restarted or player was removed)
                    console.log('Session invalid or player not found, redirecting to join page...');
                    showNotificationAndRedirect(
                        'Session Expired',
                        'The server has been updated or restarted.',
                        '#f1c40f'
                    );
                }
            })
            .catch(error => {
                console.error('Error fetching game state:', error);
                // If we can't connect to the server for a while, also redirect
                if (window.gameStateErrorCount === undefined) {
                    window.gameStateErrorCount = 1;
                } else {
                    window.gameStateErrorCount++;
                }

                // After 5 consecutive errors, redirect to join page
                if (window.gameStateErrorCount >= 5) {
                    console.log('Multiple connection errors, redirecting to join page...');
                    showNotificationAndRedirect(
                        'Connection Lost',
                        'Unable to connect to the game server.',
                        '#e74c3c'
                    );
                }
            });
    }

    // Function to extract YouTube video ID from iframe src
    function extractVideoIdFromSrc(src) {
        if (!src) return null;

        // Handle youtube.com/embed/ format
        const embedRegex = /youtube\.com\/embed\/([^?&#]+)/;
        const embedMatch = src.match(embedRegex);
        if (embedMatch && embedMatch[1]) {
            return embedMatch[1];
        }

        return null;
    }

    // Update game state in the UI
    function updateGameState(data) {
        // Store host status
        isHost = data.is_host === true;

        // Update localPlayerName from server data if available
        if (data.my_name) {
            localPlayerName = data.my_name;
        }
        // These are the primary declarations for this function's scope
        const myName = data.my_name;
        const gameIsOver = data.game_over === true;
        const playerHasFinished = data.rankings && data.rankings.some(r => r.player_name === myName);

        // Check if game is waiting for the host to start it
        const waitingForStart = data.waiting_for_start === true;

        // Update the YouTube video if it has changed
        if (data.table_video_id) {
            const youtubeIframe = document.querySelector('.youtube-container iframe');
            if (youtubeIframe) {
                const currentVideoId = extractVideoIdFromSrc(youtubeIframe.src);
                if (currentVideoId !== data.table_video_id) {
                    const newSrc = `https://www.youtube.com/embed/${data.table_video_id}?autoplay=1&mute=1&controls=0&loop=1&playlist=${data.table_video_id}`;
                    youtubeIframe.src = newSrc;
                }
            }
        }

        // Show waiting message if game hasn't started yet
        if (waitingForStart) {
            const statusBadge = document.getElementById('cards-required-indicator');
            if (statusBadge) {
                statusBadge.innerHTML = '<span class="status-label">Waiting for host to start the game...</span>';
                statusBadge.style.backgroundColor = 'rgba(243, 156, 18, 0.2)';
                statusBadge.style.borderColor = '#f39c12';
            }
        }

        // Track skipped status changes to detect newly skipped players
        const previousSkippedStatus = {};
        if (allPlayersData && allPlayersData.length > 0) {
            allPlayersData.forEach(player => {
                previousSkippedStatus[player.id] = player.skipped;
            });
        }

        // Store all players data
        allPlayersData = data.players || [];

        // Check for newly skipped players (for matching card skip animation)
        if (data.last_action && data.last_action.includes('skipped')) {
            console.log("Detected skipped action:", data.last_action);

            // Find players that were newly skipped
            data.players.forEach(player => {
                if (player.skipped && (!previousSkippedStatus[player.id] || previousSkippedStatus[player.id] === false)) {
                    console.log("Found newly skipped player:", player.name, "at position", player.position);

                    // Show skip animation with a slight delay to make it more visible
                    setTimeout(() => {
                        showSkipAnimation(player.position);
                    }, 300);
                }
            });
        }

        // Check for last_skipped_position (from matching cards or timeout)
        if (data.last_skipped_position !== undefined) {
            console.log("Found last_skipped_position:", data.last_skipped_position);

            // Check if this was a timeout skip based on the last action message
            const isTimeout = data.last_action && data.last_action.toLowerCase().includes('timeout');

            setTimeout(() => {
                showSkipAnimation(data.last_skipped_position, isTimeout);
            }, 300);
        }

        // Store current deck size if provided
        if (data.deck_size !== undefined) {
            currentDeckSize = data.deck_size;
        }

        // Update the table border based on turn status
        const tableCircle = document.querySelector('.table-circle');
        if (tableCircle) {
            if (data.is_my_turn && !playerHasFinished && !data.game_over) {
                tableCircle.classList.add('my-turn');
            } else {
                tableCircle.classList.remove('my-turn');
            }
        }

        // Update turn timer if provided
        if (data.turn_timer) {
            startTurnTimer(data.turn_timer.time_left, data.turn_timer.duration);
        } else {
            // If no timer data, clear any existing timer
            clearInterval(turnTimerInterval);
            currentTurnTimeLeft = null; // Reset current time left
            turnTimerDuration = 20; // Reset to default duration
            updateAllPlayerTimers(); // Update UI to hide timers if not applicable
        }

        // Update card exchange state if provided
        if (data.card_exchange) {
            cardExchangeActive = data.card_exchange.active;
            isPresident = data.card_exchange.is_president;
            isCulo = data.card_exchange.is_culo;
            isVicePresident = data.card_exchange.is_vice_president;
            isViceCulo = data.card_exchange.is_vice_culo;
            presidentCardsToReceive = data.card_exchange.president_cards_to_receive || [];
            presidentCardsToGive = data.card_exchange.president_cards_to_give || [];
            vicePresidentCardToReceive = data.card_exchange.vice_president_card_to_receive;
            vicePresidentCardToGive = data.card_exchange.vice_president_card_to_give;
            presidentExchangeCompleted = data.card_exchange.president_exchange_completed;
            viceExchangeCompleted = data.card_exchange.vice_exchange_completed;
            exchangeCompleted = data.card_exchange.completed;
            currentExchange = data.card_exchange.current_exchange;
            exchangePhase = data.card_exchange.phase;
            culoHand = data.card_exchange.culo_hand || [];
            viceCuloHand = data.card_exchange.vice_culo_hand || [];

            // Check if we need to show the card exchange modal
            handleCardExchangeState(data.player_hand);
        } else {
            cardExchangeActive = false;
        }

        // Setup host controls
        setupHostControls();

        // Check for deal animation trigger
        if (data.deal_animation_pending && !hasInitialDealAnimationPlayed && !dealAnimationInProgress) {
            console.log("Deal animation triggered.");
            hasInitialDealAnimationPlayed = true; // Set this immediately to prevent re-trigger

            performDealAnimation(data, () => {
                console.log("Deal animation complete. Rendering final state.");
                // Animation complete: render the actual hand and table from data
                // These are new consts for the callback scope, which is fine.
                const animCompleteMyName = data.my_name;
                const animCompleteGameIsOver = data.game_over === true;
                const animCompletePlayerHasFinished = data.rankings && data.rankings.some(r => r.player_name === animCompleteMyName);

                renderPlayerHand(data.player_hand, data.playable_cards, data.is_my_turn, animCompleteGameIsOver, animCompletePlayerHasFinished, data.rankings, animCompleteMyName);
                renderTableCards(data.table);
                updatePlaySelectedButtonState(animCompletePlayerHasFinished);
            });
        } else if (!data.deal_animation_pending) {
            // If server says no animation is pending, reset the client-side flag.
            hasInitialDealAnimationPlayed = false;
        }

        // Store current selection indices before updating hand
        const currentSelection = [...selectedCards];

        // Update the cards required indicator
        updateCardsRequiredIndicator(data.required_cards_to_play);

        // Update rankings display
        updateRankingsDisplay(data.rankings || []);

        // Update player's hand and table only if no animation is in progress
        if (!dealAnimationInProgress) {
            // Ensure this block uses the myName, gameIsOver, playerHasFinished from the top of updateGameState
            // DO NOT redeclare them here with new const keywords.
            renderPlayerHand(data.player_hand, data.playable_cards, data.is_my_turn, gameIsOver, playerHasFinished, data.rankings, myName);
            renderTableCards(data.table);
        }

        // Update player positions
        updatePlayerPositions(data.players);

        // Re-add event listeners to new cards
        addCardListeners();

        // Organize cards in two rows
        organizeCardsInTwoRows();

        // Display chat messages
        displayChatMessages(data.chat_messages);

        // Make sure the clear system messages button is available
        addClearSystemMessagesButton();

        // Update button states
        if (skipTurnButton) {
            // Disable skip button if:
            // 1. Game is over OR
            // 2. It's not the player's turn OR
            // 3. Player has finished (has a rank) OR
            // 4. Card exchange is active and not completed
            if (gameIsOver || !data.is_my_turn || playerHasFinished || (cardExchangeActive && !exchangeCompleted)) {
                skipTurnButton.disabled = true;
            } else {
                // Enable skip button only when:
                // 1. It's the player's turn AND
                // 2. Either they have no playable cards OR the table is not empty
                const canSkip = data.is_my_turn &&
                    (!data.playable_cards.length || data.table.length > 0);
                skipTurnButton.disabled = !canSkip;
            }
        }

        // Update play selected button state (handles visibility and text)
        updatePlaySelectedButtonState(playerHasFinished);
    }

    // New function to encapsulate hand rendering
    function renderPlayerHand(handData, playableCardIndices, isMyTurn, gameIsOver, currentPlayerHasFinished, rankings, myName) {
        const currentSelection = [...selectedCards]; // Preserve selection if any
        selectedCards = [];

        playerHand.innerHTML = '';
        if (handData) {
            handData.forEach((card, index) => {
                let isDisabled = gameIsOver || !isMyTurn || currentPlayerHasFinished;
                if (!gameIsOver && isMyTurn && !currentPlayerHasFinished && playableCardIndices && !playableCardIndices.includes(index)) {
                    isDisabled = true;
                }
                const cardElement = createCardElement(card, index, isDisabled);
                if (currentSelection.includes(index) && !isDisabled) {
                    cardElement.classList.add('selected');
                    selectedCards.push(index);
                }
                playerHand.appendChild(cardElement);
            });
        }
        addCardListeners();
        organizeCardsInTwoRows();
        updatePlaySelectedButtonState(currentPlayerHasFinished);
    }

    // New function to encapsulate table rendering
    function renderTableCards(tableData) {
        tableCards.innerHTML = '';
        if (tableData) {
            const tableCardsArray = [...tableData];
            tableCardsArray.forEach(card => {
                const cardElement = createCardElement(card, null, true); // Table cards are always "disabled" for clicking
                cardElement.classList.add('table-card');
                tableCards.appendChild(cardElement);
            });

            if (tableCardsArray.length > 0) {
                const lastCard = tableCardsArray[tableCardsArray.length - 1];
                const lastCardElement = tableCards.lastChild;
                if (lastCardElement && lastCard.id && lastCard.id !== lastAnimatedCardId) {
                    lastCardElement.classList.add('played');
                    lastAnimatedCardId = lastCard.id;
                }
            }
        }
    }

    async function performDealAnimation(gameStateData, onCompleteCallback) {
        console.log("Performing deal animation for player:", gameStateData.my_name);
        dealAnimationInProgress = true; // Set flag

        const myHandData = gameStateData.player_hand;
        const numCardsToAnimate = myHandData ? myHandData.length : 0;

        playerHand.innerHTML = ''; // Clear hand for animation
        if (!tableCircleElement) {
            console.error("Table circle element not found for animation origin.");
            dealAnimationInProgress = false;
            if (onCompleteCallback) onCompleteCallback();
            return;
        }
        const handRect = playerHand.getBoundingClientRect();
        const tableRect = tableCircleElement.getBoundingClientRect();

        const tableCenterX = tableRect.left + tableRect.width / 2;
        const tableCenterY = tableRect.top + tableRect.height / 2;

        const cardPromises = [];

        for (let i = 0; i < numCardsToAnimate; i++) {
            const cardData = myHandData[i];
            const cardElement = createCardElement(cardData, i, true); // Create card, initially disabled

            cardElement.style.position = 'fixed';
            cardElement.style.left = `${tableCenterX - cardElement.offsetWidth / 2}px`;
            cardElement.style.top = `${tableCenterY - cardElement.offsetHeight / 2}px`;
            cardElement.style.transform = 'scale(0.5) rotate(' + (Math.random() * 30 - 15) + 'deg)';
            cardElement.style.opacity = '0';
            cardElement.style.zIndex = '3000';
            document.body.appendChild(cardElement);

            // Approximate target position in hand, considering scroll and layout
            const cardWidth = 60; // From CSS
            const cardGap = 8; // From CSS for .two-row-hand gap
            const cardsPerRow = Math.floor(playerHand.clientWidth / (cardWidth + cardGap)) || 5;
            const targetCol = i % cardsPerRow;
            const targetRow = Math.floor(i / cardsPerRow);

            const targetXInHand = targetCol * (cardWidth + cardGap) + playerHand.scrollLeft;
            const targetYInHand = targetRow * (cardElement.offsetHeight + cardGap); // Assuming card height is consistent

            const targetPageX = handRect.left + targetXInHand;
            const targetPageY = handRect.top + targetYInHand;

            const promise = new Promise(async (resolve) => {
                await new Promise(r => setTimeout(r, i * DEAL_ANIMATION_STAGGER_DELAY));

                cardElement.style.transition = `all ${DEAL_ANIMATION_CARD_DURATION / 1000}s ease-out`;
                void cardElement.offsetWidth; // Trigger reflow

                cardElement.style.left = `${targetPageX}px`;
                cardElement.style.top = `${targetPageY}px`;
                cardElement.style.transform = 'scale(1) rotate(0deg)';
                cardElement.style.opacity = '1';

                setTimeout(() => {
                    if (cardElement.parentNode === document.body) {
                        document.body.removeChild(cardElement);
                    }
                    resolve();
                }, DEAL_ANIMATION_CARD_DURATION + 50);
            });
            cardPromises.push(promise);
        }

        await Promise.all(cardPromises);

        dealAnimationInProgress = false; // Clear flag
        if (onCompleteCallback) {
            onCompleteCallback();
        }
    }

    // Function to organize cards in two rows
    function organizeCardsInTwoRows() {
        // This is now handled by CSS grid layout
        // Just a placeholder for future enhancements if needed
    }

    // Update player positions around the table
    function updatePlayerPositions(players) {
        const playerPositionsContainer = document.querySelector('.player-positions');
        if (!playerPositionsContainer) {
            console.error("Player positions container not found!");
            return;
        }

        // Get all current player elements on the page
        const existingPlayerElements = playerPositionsContainer.querySelectorAll('.player-position');
        const existingPlayerMap = new Map();
        existingPlayerElements.forEach(el => {
            const playerId = el.dataset.playerId;
            if (playerId) {
                existingPlayerMap.set(playerId, el);
            }
        });

        const currentPlayerIdsInData = new Set(players.map(p => p.id));

        // Remove players who are no longer in the game state
        existingPlayerMap.forEach((el, playerId) => {
            if (!currentPlayerIdsInData.has(playerId)) {
                el.remove();
                existingPlayerMap.delete(playerId);
            }
        });

        // Add or update players
        players.forEach(player => {
            let playerElement = existingPlayerMap.get(player.id);

            // Track if player was newly skipped
            let wasSkipped = false;
            let newlySkipped = false;

            if (playerElement) {
                wasSkipped = playerElement.classList.contains('skipped') && !player.skipped;
                newlySkipped = !playerElement.classList.contains('skipped') && player.skipped;
            }

            if (!playerElement) {
                // Player doesn't exist, create new element
                playerElement = document.createElement('div');
                playerElement.dataset.playerId = player.id;
                // The structure should match game.html template for a player-position
                playerElement.innerHTML = `
                    <div class="player-avatar"></div>
                    <div class="player-name-tag"></div>
                    <div class="card-count">
                        <span class="card-count-number">0</span> cards
                    </div>
                    <div class="turn-timer-container">
                        <div class="turn-timer-bar"></div>
                        <div class="turn-timer-text"></div>
                    </div>
                `;
                playerPositionsContainer.appendChild(playerElement);

                // If player is skipped on creation, mark as newly skipped
                if (player.skipped) {
                    newlySkipped = true;
                }
            }

            // Update common attributes (class for positioning, current turn, name, card count)
            // First, save the skipped class if it exists
            const wasSkippedClass = playerElement.classList.contains('skipped');

            // Reset all classes and apply position class
            playerElement.className = 'player-position position-' + player.position;

            // Re-apply skipped class if player is skipped
            if (player.skipped) {
                playerElement.classList.add('skipped');
                console.log(`Player ${player.name} is marked as skipped`);
            }

            playerElement.style.display = 'flex'; // Make sure it's visible

            const avatar = playerElement.querySelector('.player-avatar');
            const nameTag = playerElement.querySelector('.player-name-tag');
            const cardCountNumber = playerElement.querySelector('.card-count-number');
            const timerText = playerElement.querySelector('.turn-timer-text');
            // The text " cards" is part of the static innerHTML, so we only update the number.

            if (avatar) {
                // Reset all classes first
                avatar.className = 'player-avatar';

                // Set initial content
                avatar.textContent = player.name ? player.name[0].toUpperCase() : '?';

                // Add current turn indicator if applicable
                if (player.is_current) {
                    avatar.classList.add('current-turn');
                }

                // Add rank indicator if player has a rank
                if (player.rank) {
                    avatar.classList.add('rank-' + player.rank);
                }

                // Add role indicator if player has a non-neutral role
                if (player.role && player.role !== 'neutral') {
                    avatar.classList.add('role-' + player.role);
                }

                // Add host indicator if player is host
                if (player.is_host) {
                    avatar.classList.add('is-host');
                }
            }

            if (nameTag) {
                // Reset name tag classes first
                nameTag.className = 'player-name-tag';

                // Set name
                nameTag.textContent = player.name || 'Joining...';

                // Add rank to name tag if player has a rank
                if (player.rank) {
                    nameTag.classList.add('rank-' + player.rank);
                }

                // Add role to name tag if player has a non-neutral role
                if (player.role && player.role !== 'neutral') {
                    nameTag.classList.add('role-' + player.role);
                }

                // Add host indicator to name tag if player is host
                if (player.is_host) {
                    nameTag.classList.add('is-host');
                }
            }

            if (cardCountNumber) {
                cardCountNumber.textContent = player.hand_count;
            }

            // Update turn timer bar if this is the current player
            if (player.is_current) {
                updateTurnTimerBar(playerElement);
            } else {
                // Hide timer bar for non-current players
                const timerContainer = playerElement.querySelector('.turn-timer-container');
                if (timerContainer) {
                    timerContainer.style.display = 'none';
                }
            }

            // Update timer text if it exists
            if (timerText) {
                const secondsLeft = Math.ceil(currentTurnTimeLeft);
                timerText.textContent = `${secondsLeft}s`;
            }
        });
    }

    // Function to update the turn timer bar
    function updateTurnTimerBar(playerElement) {
        const timerContainer = playerElement.querySelector('.turn-timer-container');
        const timerBar = playerElement.querySelector('.turn-timer-bar');
        const timerText = playerElement.querySelector('.turn-timer-text');

        if (!timerContainer || !timerBar) return;

        // Show the timer container
        timerContainer.style.display = 'block';

        // Reset timer bar classes
        timerBar.className = 'turn-timer-bar';

        // Reset timer text classes if it exists
        if (timerText) {
            timerText.className = 'turn-timer-text';
        }

        // Check if sand clock already exists, if not create it
        let sandClock = playerElement.querySelector('.sand-clock');
        if (!sandClock) {
            sandClock = document.createElement('div');
            sandClock.className = 'sand-clock';
            playerElement.appendChild(sandClock);
        }

        // If we have timer data, update the bar
        if (currentTurnTimeLeft !== null && turnTimerDuration > 0) {
            const percentage = (currentTurnTimeLeft / turnTimerDuration) * 100;
            timerBar.style.width = `${percentage}%`;

            // Update timer text if it exists
            if (timerText) {
                const secondsLeft = Math.ceil(currentTurnTimeLeft);
                timerText.textContent = `${secondsLeft}s`;

                // Add warning/danger classes based on time left
                if (percentage <= 30) {
                    timerText.classList.add('danger');
                } else if (percentage <= 60) {
                    timerText.classList.add('warning');
                }
            }

            // Add warning/danger classes based on time left
            if (percentage <= 30) {
                timerBar.classList.add('danger', 'blinking');
                // Show sand clock when timer is in danger zone
                sandClock.classList.add('visible');
            } else if (percentage <= 60) {
                timerBar.classList.add('warning');
                // Hide sand clock when not in danger zone
                sandClock.classList.remove('visible');
            } else {
                // Hide sand clock when timer is good
                sandClock.classList.remove('visible');
            }
        } else {
            // If no timer data, hide the container and sand clock
            timerContainer.style.display = 'none';
            sandClock.classList.remove('visible');
        }
    }

    // Function to start the turn timer
    function startTurnTimer(timeLeft, duration) {
        // Clear any existing interval
        clearInterval(turnTimerInterval);

        // Set initial values
        currentTurnTimeLeft = timeLeft;
        turnTimerDuration = duration;

        // Update all player elements to show/hide timer as appropriate
        updateAllPlayerTimers();

        // Start the interval to update the timer
        turnTimerInterval = setInterval(() => {
            // Decrease time left
            currentTurnTimeLeft = Math.max(0, currentTurnTimeLeft - 0.1);

            // Update the timer display
            updateAllPlayerTimers();

            // If time is up, clear the interval
            if (currentTurnTimeLeft <= 0) {
                clearInterval(turnTimerInterval);
                // fetchGameState(); // Server will handle auto-skip, client will refresh via polling
            }
        }, 100); // Update every 100ms for smoother animation
    }

    // Function to update all player timer bars
    function updateAllPlayerTimers() {
        const playerPositions = document.querySelectorAll('.player-position');
        playerPositions.forEach(playerElement => {
            const avatar = playerElement.querySelector('.player-avatar');
            if (avatar && avatar.classList.contains('current-turn')) {
                updateTurnTimerBar(playerElement);
            } else {
                // Hide timer for non-current players
                const timerContainer = playerElement.querySelector('.turn-timer-container');
                if (timerContainer) {
                    timerContainer.style.display = 'none';
                }
            }
        });
    }

    // Create a card element
    function createCardElement(card, index = null, disabled = false) {
        const cardDiv = document.createElement('div');
        cardDiv.className = 'card';
        if (disabled) {
            cardDiv.classList.add('disabled');
        }

        cardDiv.dataset.suit = card.suit;
        cardDiv.dataset.value = card.value;
        if (index !== null) {
            cardDiv.dataset.index = index;
        }

        // Add title attribute for joker cards (2s)
        if (card.value === '2') {
            cardDiv.title = "Joker: This card can be played on any other card regardless of value";
        }

        // Determine the display value (for jokers that have been assigned a value)
        let displayValue = card.value;
        let isJokerWithValue = false;

        if (card.value === '2' && card.joker_value) {
            displayValue = card.joker_value;
            isJokerWithValue = true;
        }

        // Format the display text
        let valueText = displayValue;
        if (['jack', 'queen', 'king', 'ace'].includes(displayValue)) {
            valueText = displayValue.charAt(0).toUpperCase();
        }

        cardDiv.innerHTML = `
            <div class="card-inner">
                <div class="card-front">
                    <div class="card-suit corner top-left ${card.suit}"></div>
                    <div class="card-value center">
                        ${valueText}
                        ${isJokerWithValue ? '<span class="joker-indicator">*</span>' : ''}
                    </div>
                    <div class="card-suit corner bottom-right ${card.suit}"></div>
                </div>
                <div class="card-back">
                    <div class="card-back-design"></div>
                </div>
            </div>
        `;

        return cardDiv;
    }

    // Initialize event listeners
    addCardListeners();
    organizeCardsInTwoRows();

    // Add event listener for play selected button
    if (playSelectedButton) {
        playSelectedButton.addEventListener('click', () => {
            // Get the values of all selected cards
            const selectedCardValues = selectedCards.map(index => {
                const cardElement = playerHand.querySelector(`.card[data-index="${index}"]`);
                return cardElement ? cardElement.dataset.value : null;
            }).filter(value => value !== null); // Filter out null if card not found

            const hasJoker = selectedCardValues.some(value => value === '2');
            const allJokers = selectedCardValues.length > 0 && selectedCardValues.every(value => value === '2');

            if (hasJoker && allJokers) { // Only show modal if ALL selected cards are jokers
                showJokerValueSelection(selectedCards);
            } else {
                // If there's a mix of jokers and non-jokers, or no jokers at all,
                // playSelectedCards() will be called.
                // The playSelectedCards function (modified previously) will auto-assign
                // the jokerValue if it's a mixed selection (e.g., a King and a Joker).
                playSelectedCards();
            }
        });
    }

    // Chat functionality
    function handleSendMessage() {
        const messageText = chatMessageInput.value.trim();
        if (messageText === '') {
            return; // Don't send empty messages
        }

        sendMessageButton.disabled = true; // Disable button while sending
        const tempId = `local-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const originalInput = chatMessageInput.value;

        // Optimistic UI update
        const optimisticMessage = {
            sender: localPlayerName, // Use the stored local player name
            text: messageText,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            id: tempId,
        };
        appendMessageToChatLog(optimisticMessage);
        chatMessageInput.value = ''; // Clear input now

        fetch('/send_message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: messageText }), // Send original messageText
        })
            .then(response => response.json())
            .then(serverData => {
                if (!serverData.success) { // Handle failure from server
                    console.error('Error sending message:', serverData.error);
                    const optimisticElement = chatLog.querySelector(`.chat-message[data-message-id='${tempId}']`);
                    if (optimisticElement) optimisticElement.remove();
                    chatMessageInput.value = originalInput; // Restore input
                    alert("Failed to send message: " + (serverData.error || "Unknown error"));
                }
                // On success, the next fetchGameState will update the chat from the server,
                // which includes clearing and re-rendering, effectively removing the optimistic message
                // and showing the server-confirmed one.
            })
            .catch(error => { // Handle network or other fetch errors
                console.error('Error sending message:', error);
                const optimisticElement = chatLog.querySelector(`.chat-message[data-message-id='${tempId}']`);
                if (optimisticElement) optimisticElement.remove();
                chatMessageInput.value = originalInput; // Restore input
                alert("Error sending message.");
            })
            .finally(() => {
                sendMessageButton.disabled = false; // Re-enable button
                chatMessageInput.focus(); // Focus back on input
            });
    }

    if (sendMessageButton && chatMessageInput) {
        sendMessageButton.addEventListener('click', handleSendMessage);
        chatMessageInput.addEventListener('keypress', (event) => {
            if (event.key === 'Enter') {
                handleSendMessage();
            }
        });
    }

    let lastDisplayedMessageId = null;

    function displayChatMessages(messages) {
        if (!chatLog) return;

        let shouldScroll = chatLog.scrollTop + chatLog.clientHeight >= chatLog.scrollHeight - 20;

        chatLog.innerHTML = ''; // Clear all existing messages

        messages.forEach(msg => {
            const messageElement = createChatMessageElement(msg);

            // Make system messages collapsible
            if (msg.sender === 'System' && msg.type !== 'divider') {
                messageElement.classList.add('collapsed');

                // Add click event to toggle collapsed state
                messageElement.addEventListener('click', function () {
                    this.classList.toggle('collapsed');
                });

                // If system messages are currently hidden, hide this message too
                if (systemMessagesHidden) {
                    messageElement.style.display = 'none';
                }
            }

            chatLog.appendChild(messageElement);
        });

        if (shouldScroll) {
            chatLog.scrollTop = chatLog.scrollHeight;
        }
    }

    // Poll for game state updates more frequently to keep the timer accurate
    setInterval(fetchGameState, 1000);

    // Function to update the cards required indicator
    function updateCardsRequiredIndicator(requiredCards) {
        const indicator = document.getElementById('cards-required-indicator');
        if (!indicator) return;

        // Update the text
        let statusLabel = "Playing singles";
        if (requiredCards > 1) {
            statusLabel = `Playing ${requiredCards} cards`;
        }

        // Update the indicator content
        indicator.innerHTML = `<span class="status-label">${statusLabel}</span>`;

        // Update the styling based on the number of cards
        indicator.className = "status-badge"; // Reset classes

        // Add specific styling based on the number of cards
        if (requiredCards === 2) {
            indicator.style.backgroundColor = "rgba(241, 196, 15, 0.2)";
            indicator.style.borderColor = "#f1c40f";
        } else if (requiredCards === 3) {
            indicator.style.backgroundColor = "rgba(231, 76, 60, 0.2)";
            indicator.style.borderColor = "#e74c3c";
        } else if (requiredCards >= 4) {
            indicator.style.backgroundColor = "rgba(155, 89, 182, 0.2)";
            indicator.style.borderColor = "#9b59b6";
        } else {
            // Default styling for singles (already in CSS)
            indicator.style.backgroundColor = "rgba(52, 152, 219, 0.2)";
            indicator.style.borderColor = "#3498db";
        }
    }

    // Function to update the rankings display
    function updateRankingsDisplay(rankings) {
        const rankingsContainer = document.getElementById('rankings-display');
        if (!rankingsContainer) return;

        // Clear previous rankings
        rankingsContainer.innerHTML = '';

        // If no rankings, hide the container
        if (!rankings || rankings.length === 0) {
            rankingsContainer.style.display = 'none';
            return;
        }

        // Show the container
        rankingsContainer.style.display = 'flex';

        // Add ranking items
        rankings.forEach(rank => {
            const rankItem = document.createElement('div');
            rankItem.className = `ranking-item ranking-${rank.rank}`;

            let rankIcon = '';
            switch (rank.rank) {
                case 'gold':
                    rankIcon = '👑';
                    break;
                case 'silver':
                    rankIcon = '🥈';
                    break;
                case 'bronze':
                    rankIcon = '🥉';
                    break;
                case 'loser':
                    rankIcon = '👎';
                    break;
            }

            rankItem.innerHTML = `
                <span class="ranking-icon">${rankIcon}</span>
                <span class="ranking-name">${rank.player_name}</span>
            `;

            rankingsContainer.appendChild(rankItem);
        });
    }

    // Host controls functionality
    function setupHostControls() {
        // Show host controls if player is host
        if (isHost && hostControlsPanel) {
            hostControlsPanel.style.display = 'block';
        } else if (hostControlsPanel) {
            hostControlsPanel.style.display = 'none';
        }

        // Host start game button
        if (hostStartGameButton) {
            // Remove any existing event listeners
            const freshStartGameButton = document.getElementById('host-start-game');
            if (freshStartGameButton) {
                // Show/hide based on game state
                const waitingForStart = document.getElementById('cards-required-indicator')?.innerText.includes('Waiting for host');
                freshStartGameButton.style.display = waitingForStart ? 'block' : 'none';

                // Clone and replace to remove all event listeners
                const newButton = freshStartGameButton.cloneNode(true);
                freshStartGameButton.parentNode.replaceChild(newButton, freshStartGameButton);

                // Add a single event listener to the new button
                newButton.addEventListener('click', function (e) {
                    e.preventDefault();
                    if (confirm('Are you sure you want to start the game?')) {
                        // Disable the button temporarily to prevent multiple clicks
                        this.disabled = true;

                        fetch('/start_game', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            }
                        })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success && data.refresh) {
                                    fetchGameState();
                                } else if (data.error) {
                                    alert(data.error);
                                    this.disabled = false; // Re-enable the button on error
                                }
                            })
                            .catch(error => {
                                console.error('Error starting game:', error);
                                alert('Failed to start the game. Please try again.');
                                this.disabled = false; // Re-enable the button on error
                            });
                    }
                });
            }
        }

        // Host new game button
        if (hostNewGameButton) {
            // Remove any existing event listeners
            const freshNewGameButton = document.getElementById('host-new-game');
            if (freshNewGameButton) {
                // Clone and replace to remove all event listeners
                const newButton = freshNewGameButton.cloneNode(true);
                freshNewGameButton.parentNode.replaceChild(newButton, freshNewGameButton);

                // Add a single event listener to the new button
                newButton.addEventListener('click', function (e) {
                    e.preventDefault();
                    if (confirm('Are you sure you want to start a new game?')) {
                        // Disable the button temporarily to prevent multiple clicks
                        this.disabled = true;

                        fetch('/reset_game', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            }
                        })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success && data.refresh) {
                                    fetchGameState();
                                } else if (data.error) {
                                    alert(data.error);
                                    this.disabled = false; // Re-enable the button on error
                                }
                            })
                            .catch(error => {
                                console.error('Error starting new game:', error);
                                alert('Failed to start a new game. Please try again.');
                                this.disabled = false; // Re-enable the button on error
                            });
                    }
                });
            }
        }

        // Host reset game button
        if (hostResetGameButton) {
            // Remove any existing event listeners
            const freshResetButton = document.getElementById('host-reset-game');
            if (freshResetButton) {
                // Clone and replace to remove all event listeners
                const newButton = freshResetButton.cloneNode(true);
                freshResetButton.parentNode.replaceChild(newButton, freshResetButton);

                // Add a single event listener to the new button
                newButton.addEventListener('click', function (e) {
                    e.preventDefault();
                    if (confirm('Are you sure you want to reset the game?')) {
                        // Disable the button temporarily to prevent multiple clicks
                        this.disabled = true;

                        fetch('/reset_game', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            }
                        })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success && data.refresh) {
                                    fetchGameState();
                                } else if (data.error) {
                                    alert(data.error);
                                    this.disabled = false; // Re-enable the button on error
                                }
                            })
                            .catch(error => {
                                console.error('Error resetting game:', error);
                                alert('Failed to reset the game. Please try again.');
                                this.disabled = false; // Re-enable the button on error
                            });
                    }
                });
            }
        }

        // Host assign ranks button
        if (hostAssignRanksButton) {
            // Remove any existing event listeners
            hostAssignRanksButton.replaceWith(hostAssignRanksButton.cloneNode(true));
            // Get the fresh element
            const freshAssignRanksButton = document.getElementById('host-assign-ranks');
            if (freshAssignRanksButton) {
                freshAssignRanksButton.addEventListener('click', showRankAssignmentModal);
            }
        }

        // Host assign roles button
        if (hostAssignRolesButton) {
            // Remove any existing event listeners
            const freshAssignRolesButton = document.getElementById('host-assign-roles');
            if (freshAssignRolesButton) {
                // Clone and replace to remove all event listeners
                const newButton = freshAssignRolesButton.cloneNode(true);
                freshAssignRolesButton.parentNode.replaceChild(newButton, freshAssignRolesButton);

                // Add a single event listener to the new button
                newButton.addEventListener('click', function (e) {
                    e.preventDefault();
                    showRoleAssignmentModal();
                });
            }
        }

        // Host change deck button
        if (hostChangeDeckButton) {
            // Remove any existing event listeners
            const freshChangeDeckButton = document.getElementById('host-change-deck');
            if (freshChangeDeckButton) {
                // Clone and replace to remove all event listeners
                const newButton = freshChangeDeckButton.cloneNode(true);
                freshChangeDeckButton.parentNode.replaceChild(newButton, freshChangeDeckButton);

                // Add a single event listener to the new button
                newButton.addEventListener('click', function (e) {
                    e.preventDefault();
                    showDeckSizeModal();
                });
            }
        }

        // Host kick players button
        if (hostKickPlayersButton) {
            // Remove any existing event listeners
            const freshKickPlayersButton = document.getElementById('host-kick-players');
            if (freshKickPlayersButton) {
                // Clone and replace to remove all event listeners
                const newButton = freshKickPlayersButton.cloneNode(true);
                freshKickPlayersButton.parentNode.replaceChild(newButton, freshKickPlayersButton);

                // Add a single event listener to the new button
                newButton.addEventListener('click', function (e) {
                    e.preventDefault();
                    showKickPlayersModal();
                });
            }
        }

        // Role assignment modal buttons
        if (saveRolesButton) {
            // Remove any existing event listeners
            const freshSaveRolesButton = document.getElementById('save-roles-btn');
            if (freshSaveRolesButton) {
                // Clone and replace to remove all event listeners
                const newButton = freshSaveRolesButton.cloneNode(true);
                freshSaveRolesButton.parentNode.replaceChild(newButton, freshSaveRolesButton);

                // Add a single event listener to the new button
                newButton.addEventListener('click', function (e) {
                    e.preventDefault();
                    savePlayerRoles();
                });
            }
        }

        if (cancelRolesButton) {
            // Remove any existing event listeners
            const freshCancelRolesButton = document.getElementById('cancel-roles-btn');
            if (freshCancelRolesButton) {
                // Clone and replace to remove all event listeners
                const newButton = freshCancelRolesButton.cloneNode(true);
                freshCancelRolesButton.parentNode.replaceChild(newButton, freshCancelRolesButton);

                // Add a single event listener to the new button
                newButton.addEventListener('click', function (e) {
                    e.preventDefault();
                    roleAssignmentModal.style.display = 'none';
                });
            }
        }

        // Deck size modal buttons
        if (saveDeckButton) {
            // Remove any existing event listeners
            const freshSaveDeckButton = document.getElementById('save-deck-btn');
            if (freshSaveDeckButton) {
                // Clone and replace to remove all event listeners
                const newButton = freshSaveDeckButton.cloneNode(true);
                freshSaveDeckButton.parentNode.replaceChild(newButton, freshSaveDeckButton);

                // Add a single event listener to the new button
                newButton.addEventListener('click', function (e) {
                    e.preventDefault();
                    saveDeckSize();
                });
            }
        }

        if (cancelDeckButton) {
            // Remove any existing event listeners
            const freshCancelDeckButton = document.getElementById('cancel-deck-btn');
            if (freshCancelDeckButton) {
                // Clone and replace to remove all event listeners
                const newButton = freshCancelDeckButton.cloneNode(true);
                freshCancelDeckButton.parentNode.replaceChild(newButton, freshCancelDeckButton);

                // Add a single event listener to the new button
                newButton.addEventListener('click', function (e) {
                    e.preventDefault();
                    deckSizeModal.style.display = 'none';
                });
            }
        }

        // Close modal when clicking outside
        if (roleAssignmentModal) {
            roleAssignmentModal.addEventListener('click', (event) => {
                if (event.target === roleAssignmentModal) {
                    roleAssignmentModal.style.display = 'none';
                }
            });
        }

        // Close deck size modal when clicking outside
        if (deckSizeModal) {
            deckSizeModal.addEventListener('click', (event) => {
                if (event.target === deckSizeModal) {
                    deckSizeModal.style.display = 'none';
                }
            });
        }

        // Cancel kick players button
        if (cancelKickButton) {
            // Remove any existing event listeners
            const freshCancelKickButton = document.getElementById('cancel-kick-btn');
            if (freshCancelKickButton) {
                // Clone and replace to remove all event listeners
                const newButton = freshCancelKickButton.cloneNode(true);
                freshCancelKickButton.parentNode.replaceChild(newButton, freshCancelKickButton);

                // Add a single event listener to the new button
                newButton.addEventListener('click', function (e) {
                    e.preventDefault();
                    kickPlayersModal.style.display = 'none';
                });
            }
        }

        // Close kick players modal when clicking outside
        if (kickPlayersModal) {
            kickPlayersModal.addEventListener('click', (event) => {
                if (event.target === kickPlayersModal) {
                    kickPlayersModal.style.display = 'none';
                }
            });
        }
    }

    // Show role assignment modal
    function showRoleAssignmentModal() {
        if (!roleAssignmentModal || !roleAssignmentPlayers) return;

        // Set the modal title
        const modalTitle = roleAssignmentModal.querySelector('h2');
        if (modalTitle) {
            modalTitle.textContent = 'Assign Player Roles';
        }

        // Clear previous content
        roleAssignmentPlayers.innerHTML = '';

        // Add player items
        allPlayersData.forEach(player => {
            const playerItem = document.createElement('div');
            playerItem.className = 'role-player-item';
            playerItem.dataset.playerId = player.id;

            const roleOptions = ['neutral', 'president', 'vice-president', 'vice-culo', 'culo'];
            const currentRole = player.role || 'neutral';

            // Create role display names
            const roleDisplayNames = {
                'neutral': 'Neutral',
                'president': 'President 👑',
                'vice-president': 'Vice-President 🥈',
                'vice-culo': 'Vice-Culo 💩',
                'culo': 'Culo 💩'
            };

            playerItem.innerHTML = `
                <span class="role-player-name">${player.name}</span>
                <select class="role-selector">
                    ${roleOptions.map(role =>
                `<option value="${role}" ${role === currentRole ? 'selected' : ''}>${roleDisplayNames[role]}</option>`
            ).join('')}
                </select>
            `;

            roleAssignmentPlayers.appendChild(playerItem);
        });

        // Update save button handler
        const saveButton = document.getElementById('save-roles-btn');
        if (saveButton) {
            saveButton.onclick = savePlayerRoles;
        }

        // Show modal
        roleAssignmentModal.style.display = 'flex';
    }

    // Show rank assignment modal
    function showRankAssignmentModal() {
        if (!roleAssignmentModal || !roleAssignmentPlayers) return;

        // Set the modal title
        const modalTitle = roleAssignmentModal.querySelector('h2');
        if (modalTitle) {
            modalTitle.textContent = 'Assign Player Ranks';
        }

        // Clear previous content
        roleAssignmentPlayers.innerHTML = '';

        // Add player items
        allPlayersData.forEach(player => {
            const playerItem = document.createElement('div');
            playerItem.className = 'role-player-item';
            playerItem.dataset.playerId = player.id;

            const rankOptions = ['none', 'gold', 'silver', 'bronze', 'loser'];
            const currentRank = player.rank || 'none';

            playerItem.innerHTML = `
                <span class="role-player-name">${player.name}</span>
                <select class="role-selector">
                    ${rankOptions.map(rank =>
                `<option value="${rank}" ${rank === currentRank ? 'selected' : ''}>${rank.charAt(0).toUpperCase() + rank.slice(1)}</option>`
            ).join('')}
                </select>
            `;

            roleAssignmentPlayers.appendChild(playerItem);
        });

        // Update save button handler
        const saveButton = document.getElementById('save-roles-btn');
        if (saveButton) {
            saveButton.onclick = savePlayerRanks;
        }

        // Show modal
        roleAssignmentModal.style.display = 'flex';
    }

    // Save player roles
    function savePlayerRoles() {
        if (!roleAssignmentPlayers) return;

        const playerRoles = [];
        const playerItems = roleAssignmentPlayers.querySelectorAll('.role-player-item');

        playerItems.forEach(item => {
            const playerId = item.dataset.playerId;
            const roleSelect = item.querySelector('.role-selector');
            const role = roleSelect.value;

            playerRoles.push({
                player_id: playerId,
                role: role
            });
        });

        // Send to server
        fetch('/assign_roles', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ roles: playerRoles }),
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    roleAssignmentModal.style.display = 'none';
                    fetchGameState();
                } else {
                    alert(data.error || 'Failed to assign roles');
                }
            })
            .catch(error => {
                console.error('Error assigning roles:', error);
                alert('An error occurred while trying to assign roles');
            });
    }

    // Save player ranks
    function savePlayerRanks() {
        if (!roleAssignmentPlayers) return;

        const playerRanks = [];
        const playerItems = roleAssignmentPlayers.querySelectorAll('.role-player-item');

        playerItems.forEach(item => {
            const playerId = item.dataset.playerId;
            const rankSelect = item.querySelector('.role-selector');
            const rank = rankSelect.value;

            if (rank !== 'none') {
                playerRanks.push({
                    player_id: playerId,
                    rank: rank
                });
            }
        });

        // Send to server
        fetch('/assign_ranks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ ranks: playerRanks }),
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    roleAssignmentModal.style.display = 'none';
                    fetchGameState();
                } else {
                    alert(data.error || 'Failed to assign ranks');
                }
            })
            .catch(error => {
                console.error('Error assigning ranks:', error);
                alert('An error occurred while trying to assign ranks');
            });
    }

    // Show deck size modal
    function showDeckSizeModal() {
        if (!deckSizeModal) return;

        // Set the current deck size radio button
        deckSizeRadios.forEach(radio => {
            if (parseFloat(radio.value) === currentDeckSize) {
                radio.checked = true;
            }
        });

        // Show modal
        deckSizeModal.style.display = 'flex';
    }

    // Show kick players modal
    function showKickPlayersModal() {
        if (!kickPlayersModal || !kickPlayersList) return;

        // Clear previous content
        kickPlayersList.innerHTML = '';

        // Add player items for each player except the host
        allPlayersData.forEach(player => {
            // Skip the host (current player)
            if (player.is_host) return;

            const playerItem = document.createElement('div');
            playerItem.className = 'role-player-item';
            playerItem.dataset.playerId = player.id;

            playerItem.innerHTML = `
                <span class="role-player-name">${player.name}</span>
                <button class="kick-player-btn" data-player-id="${player.id}">Kick</button>
            `;

            // Add click event to the kick button
            const kickButton = playerItem.querySelector('.kick-player-btn');
            kickButton.addEventListener('click', function () {
                const playerId = this.dataset.playerId;
                const playerName = player.name;
                if (confirm(`Are you sure you want to kick ${playerName} from the game?`)) {
                    kickPlayer(playerId);
                }
            });

            kickPlayersList.appendChild(playerItem);
        });

        // If no players to kick, show a message
        if (kickPlayersList.children.length === 0) {
            const noPlayersMessage = document.createElement('div');
            noPlayersMessage.className = 'no-players-message';
            noPlayersMessage.textContent = 'No other players in the game to kick.';
            kickPlayersList.appendChild(noPlayersMessage);
        }

        // Show modal
        kickPlayersModal.style.display = 'flex';
    }

    // Kick player function
    function kickPlayer(playerId) {
        fetch('/kick_player', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ player_id: playerId }),
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    kickPlayersModal.style.display = 'none';
                    // Show a brief notification
                    const kickedPlayerName = data.kicked_player_name;
                    const notification = document.createElement('div');
                    notification.className = 'kick-notification';
                    notification.textContent = `${kickedPlayerName} has been kicked from the game.`;
                    document.body.appendChild(notification);

                    // Remove notification after a delay
                    setTimeout(() => {
                        if (notification.parentNode) {
                            notification.parentNode.removeChild(notification);
                        }
                    }, 3000);

                    fetchGameState(); // Refresh the game state
                } else {
                    alert(data.error || 'Failed to kick player');
                }
            })
            .catch(error => {
                console.error('Error kicking player:', error);
                alert('An error occurred while trying to kick the player');
            });
    }

    // Save deck size
    function saveDeckSize() {
        const selectedDeckSize = document.querySelector('input[name="deck-size"]:checked');
        if (!selectedDeckSize) return;

        const newDeckSize = parseFloat(selectedDeckSize.value);

        fetch('/change_deck_size', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ deck_size: newDeckSize }),
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    deckSizeModal.style.display = 'none';
                    currentDeckSize = newDeckSize;
                    fetchGameState();
                } else {
                    alert(data.error || 'Failed to change deck size');
                }
            })
            .catch(error => {
                console.error('Error changing deck size:', error);
                alert('An error occurred while trying to change deck size');
            });
    }

    // Handle card exchange state
    function handleCardExchangeState(playerHand) {
        if (!cardExchangeActive || exchangeCompleted) {
            cardExchangeModal.style.display = 'none';
            return;
        }

        // Handle different exchanges and phases
        if (currentExchange === 'president' && isPresident) {
            // President exchange
            if (exchangePhase === 'receive' && presidentCardsToReceive.length < 2) {
                showCardExchangeModal(
                    'President: Select Cards to Receive (2)',
                    `Select cards that you want to receive from the Culo (${presidentCardsToReceive.length}/2):`,
                    culoHand,
                    'receive',
                    'president'
                );
            } else if (exchangePhase === 'give' && presidentCardsToGive.length < 2) {
                showCardExchangeModal(
                    'President: Select Cards to Give (2)',
                    `Select cards from your hand to give to the Culo (${presidentCardsToGive.length}/2):`,
                    playerHand,
                    'give',
                    'president'
                );
            } else {
                cardExchangeModal.style.display = 'none';
            }
        } else if (currentExchange === 'vice' && isVicePresident) {
            // Vice-President exchange
            if (exchangePhase === 'receive' && vicePresidentCardToReceive === null) {
                showCardExchangeModal(
                    'Vice-President: Select Card to Receive (1)',
                    'Select a card that you want to receive from the Vice-Culo:',
                    viceCuloHand,
                    'receive',
                    'vice'
                );
            } else if (exchangePhase === 'give' && vicePresidentCardToGive === null) {
                showCardExchangeModal(
                    'Vice-President: Select Card to Give (1)',
                    'Select a card from your hand to give to the Vice-Culo:',
                    playerHand,
                    'give',
                    'vice'
                );
            } else {
                cardExchangeModal.style.display = 'none';
            }
        } else {
            cardExchangeModal.style.display = 'none';
        }
    }

    // Show card exchange modal
    function showCardExchangeModal(title, description, cards, phase, exchangeType) {
        // Set modal content
        cardExchangeTitle.textContent = title;
        cardExchangeDescription.textContent = description;

        // Update counter display
        const counterElement = document.getElementById('card-exchange-counter');
        const counterText = counterElement.querySelector('.counter-text');
        const counterIcon = counterElement.querySelector('.counter-icon');

        // Set counter icon and text based on exchange type and phase
        if (exchangeType === 'president') {
            if (phase === 'receive') {
                counterIcon.textContent = '👑 ← 💩';
                counterText.textContent = `${presidentCardsToReceive.length}/2`;
                counterElement.title = "Cards President receives from Culo";
            } else {
                counterIcon.textContent = '👑 → 💩';
                counterText.textContent = `${presidentCardsToGive.length}/2`;
                counterElement.title = "Cards President gives to Culo";
            }
            counterElement.style.display = 'flex';
        } else if (exchangeType === 'vice') {
            if (phase === 'receive') {
                counterIcon.textContent = '🥈 ← 💩';
                counterText.textContent = '0/1';
                counterElement.title = "Card Vice-President receives from Vice-Culo";
            } else {
                counterIcon.textContent = '🥈 → 💩';
                counterText.textContent = '0/1';
                counterElement.title = "Card Vice-President gives to Vice-Culo";
            }
            counterElement.style.display = 'flex';
        } else {
            counterElement.style.display = 'none';
        }

        // Clear previous cards
        cardExchangeCards.innerHTML = '';

        // Add cards to the modal
        if (cards && cards.length > 0) {
            cards.forEach((card, index) => {
                const cardElement = createCardElement(card, index, false);
                cardElement.classList.add('exchange-card');

                // For president receive phase, disable already selected cards
                if (exchangeType === 'president' && phase === 'receive' && presidentCardsToReceive.includes(index)) {
                    cardElement.classList.add('disabled');
                    cardElement.classList.add('selected-for-exchange');
                }
                // For president give phase, disable already selected cards
                else if (exchangeType === 'president' && phase === 'give' && presidentCardsToGive.includes(index)) {
                    cardElement.classList.add('disabled');
                    cardElement.classList.add('selected-for-exchange');
                }

                // Add click event for card selection
                cardElement.addEventListener('click', function () {
                    if (!cardElement.classList.contains('disabled')) {
                        selectCardForExchange(index, phase, exchangeType);
                    }
                });

                cardExchangeCards.appendChild(cardElement);
            });
        } else {
            cardExchangeCards.innerHTML = '<p>No cards available</p>';
        }

        // Set exchange status based on phase and exchange type
        if (exchangeType === 'president') {
            if (phase === 'receive') {
                cardExchangeStatus.textContent = `Select 2 best cards to take from the Culo (${presidentCardsToReceive.length}/2)`;
            } else if (phase === 'give') {
                cardExchangeStatus.textContent = `Select 2 worst cards to give to the Culo (${presidentCardsToGive.length}/2)`;
            }
        } else if (exchangeType === 'vice') {
            if (phase === 'receive') {
                cardExchangeStatus.textContent = 'Select 1 card to take from the Vice-Culo';
            } else if (phase === 'give') {
                cardExchangeStatus.textContent = 'Select 1 card to give to the Vice-Culo';
            }
        }

        // Reset status color
        cardExchangeStatus.style.color = '#bdc3c7';

        // Show modal
        cardExchangeModal.style.display = 'flex';
    }

    // Select card for exchange
    function selectCardForExchange(cardIndex, phase, exchangeType) {
        console.log(`Selecting card for exchange: ${cardIndex}, phase: ${phase}, type: ${exchangeType}`);

        // Immediately update UI for better user experience
        const selectedCard = cardExchangeCards.querySelector(`.card[data-index="${cardIndex}"]`);
        if (selectedCard) {
            selectedCard.classList.add('disabled');
            selectedCard.classList.add('selected-for-exchange');

            // Add a visual indicator of selection with emoji
            const selectionIndicator = document.createElement('div');
            selectionIndicator.className = 'selection-indicator';

            if (phase === 'receive') {
                selectionIndicator.textContent = exchangeType === 'president' ? '👑' : '🥈';
                selectionIndicator.title = exchangeType === 'president' ? 'Selected for President' : 'Selected for Vice-President';
            } else {
                selectionIndicator.textContent = '💩';
                selectionIndicator.title = exchangeType === 'president' ? 'Selected for Culo' : 'Selected for Vice-Culo';
            }

            selectedCard.appendChild(selectionIndicator);

            // Update counter immediately for better feedback
            const counterElement = document.getElementById('card-exchange-counter');
            const counterText = counterElement.querySelector('.counter-text');

            if (exchangeType === 'president') {
                if (phase === 'receive') {
                    // Optimistically update (will be corrected if server response differs)
                    const newCount = presidentCardsToReceive.length + 1;
                    counterText.textContent = `${newCount}/2`;
                } else if (phase === 'give') {
                    const newCount = presidentCardsToGive.length + 1;
                    counterText.textContent = `${newCount}/2`;
                }
            } else if (exchangeType === 'vice') {
                counterText.textContent = '1/1';
            }
        }

        // Send card selection to server
        fetch('/exchange_card', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                card_index: cardIndex,
                phase: phase,
                exchange_type: exchangeType
            }),
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // For president exchange, we may need to select multiple cards
                    if (exchangeType === 'president') {
                        if (data.cards_selected && data.cards_needed) {
                            // Still need to select more cards
                            cardExchangeStatus.textContent = `${data.message} (${data.cards_selected}/${data.cards_needed})`;

                            // Don't refresh yet, wait for all cards to be selected
                        } else {
                            // All cards selected for this phase
                            if (data.next_phase === 'give') {
                                cardExchangeStatus.textContent = '✅ Cards selected! Now select cards to give.';
                            } else {
                                cardExchangeStatus.textContent = data.message || '✅ Exchange completed!';
                            }

                            // Add completion animation
                            cardExchangeModal.classList.add('exchange-completed');

                            // Hide modal after a delay and refresh
                            setTimeout(() => {
                                cardExchangeModal.style.display = 'none';
                                cardExchangeModal.classList.remove('exchange-completed');
                                fetchGameState();
                            }, 1500);
                        }
                    } else {
                        // Vice exchange is simpler, just one card at a time
                        // Update UI based on phase
                        if (phase === 'receive') {
                            cardExchangeStatus.textContent = '✅ Card selected! Now select a card to give.';
                        } else if (phase === 'give') {
                            cardExchangeStatus.textContent = '✅ Card exchange completed!';
                        }

                        // Hide modal after a delay and refresh
                        setTimeout(() => {
                            cardExchangeModal.style.display = 'none';
                            cardExchangeModal.classList.remove('exchange-completed');
                            fetchGameState();
                        }, 1500);
                    }
                } else {
                    // Show error
                    cardExchangeStatus.textContent = data.error || 'An error occurred during card exchange.';
                    cardExchangeStatus.style.color = '#e74c3c';

                    // Remove the selection indicator if there was an error
                    if (selectedCard) {
                        selectedCard.classList.remove('disabled');
                        selectedCard.classList.remove('selected-for-exchange');
                        const indicator = selectedCard.querySelector('.selection-indicator');
                        if (indicator) {
                            indicator.remove();
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Error in card exchange:', error);
                cardExchangeStatus.textContent = 'Network error during card exchange.';
                cardExchangeStatus.style.color = '#e74c3c';

                // Remove the selection indicator if there was an error
                if (selectedCard) {
                    selectedCard.classList.remove('disabled');
                    selectedCard.classList.remove('selected-for-exchange');
                    const indicator = selectedCard.querySelector('.selection-indicator');
                    if (indicator) {
                        indicator.remove();
                    }
                }
            });
    }

    // Add this to your CSS via style tag
    const cardExchangeStyles = document.createElement('style');
    cardExchangeStyles.textContent = `
        .card-exchange-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.8);
            z-index: 2000;
            justify-content: center;
            align-items: center;
        }
        
        .card-exchange-content {
            background-color: #34495e;
            padding: 20px;
            border-radius: 10px;
            max-width: 700px;
            width: 90%;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
            text-align: center;
            border: 2px solid #f1c40f;
            position: relative;
        }
        
        .card-exchange-content h2 {
            color: #f1c40f;
            margin-bottom: 15px;
        }
        
        .card-exchange-content p {
            color: #ecf0f1;
            margin-bottom: 20px;
        }
        
        .card-exchange-counter {
            position: absolute;
            top: 10px;
            right: 10px;
            background-color: rgba(0, 0, 0, 0.6);
            border-radius: 20px;
            padding: 5px 12px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.2em;
            color: #ecf0f1;
            border: 1px solid #f1c40f;
        }
        
        .counter-icon {
            font-size: 1.3em;
        }
        
        .counter-text {
            font-weight: bold;
        }
        
        .card-exchange-cards {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: center;
            margin-bottom: 20px;
            max-height: 300px;
            overflow-y: auto;
        }
        
        .card-exchange-cards .card {
            margin: 5px;
            cursor: pointer;
            transition: transform 0.2s;
            position: relative;
        }
        
        .card-exchange-cards .card:hover:not(.disabled) {
            transform: translateY(-10px);
            box-shadow: 0 0 15px rgba(52, 152, 219, 0.7);
        }
        
        .card-exchange-info {
            background-color: rgba(0, 0, 0, 0.2);
            padding: 10px;
            border-radius: 5px;
            margin-top: 15px;
        }
        
        .card-exchange-info p {
            margin: 0;
            color: #bdc3c7;
        }
        
        .selection-indicator {
            position: absolute;
            top: -10px;
            right: -10px;
            background-color: rgba(0, 0, 0, 0.7);
            border-radius: 50%;
            width: 30px;
            height: 30px;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 16px;
            border: 2px solid #f1c40f;
            z-index: 10;
            animation: pulse 1.5s infinite;
        }
        
        .selected-for-exchange {
            box-shadow: 0 0 15px rgba(241, 196, 15, 0.8) !important;
            border: 2px solid #f1c40f !important;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        .exchange-completed {
            animation: exchange-success 1.5s;
        }
        
        @keyframes exchange-success {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); background-color: rgba(0, 0, 0, 0.9); }
            100% { transform: scale(1); }
        }
        
        .skip-animation {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 2em;
            color: #e74c3c;
            animation: pulse 1.5s infinite;
        }
        
        .skipped {
            opacity: 0.7;
            border: 2px solid #e74c3c;
        }
        
        .skip-flash {
            animation: skip-flash 0.5s;
        }
        
        @keyframes skip-flash {
            0% { background-color: #34495e; }
            50% { background-color: #e74c3c; }
            100% { background-color: #34495e; }
        }
    `;
    document.head.appendChild(cardExchangeStyles);

    // Initialize host controls
    setupHostControls();

    // Start polling for game state
    fetchGameState();

    // Function to show skip animation on a player
    function showSkipAnimation(playerPosition, isTimeout = false) {
        console.log("Showing skip animation for position:", playerPosition, isTimeout ? "(timeout)" : "");
        const playerElement = document.querySelector(`.player-position.position-${playerPosition}`);
        if (playerElement) {
            // Remove any existing animation first
            const existingAnimation = playerElement.querySelector('.skip-animation');
            if (existingAnimation) {
                existingAnimation.remove();
            }

            // Create and add skip animation element
            const skipAnimation = document.createElement('div');
            skipAnimation.className = 'skip-animation';

            // If it's a timeout, add sand clock icon instead of prohibition sign
            if (isTimeout) {
                skipAnimation.textContent = "⏳";
                skipAnimation.style.backgroundColor = "rgba(243, 156, 18, 0.95)"; // Orange for timeout
                skipAnimation.style.borderColor = "#f39c12";
            } else {
                skipAnimation.textContent = "⛔"; // Prohibition sign for regular skip
            }

            playerElement.appendChild(skipAnimation);

            // We don't add the skipped class to the player element
            // as we want the animation but not the persistent skipped state

            // Add flash effect to the table
            const tableCircle = document.querySelector('.table-circle');
            if (tableCircle) {
                // Remove the animation class first to reset it
                tableCircle.classList.remove('skip-flash');
                // Force a reflow to ensure the animation plays again
                void tableCircle.offsetWidth;
                // Add the animation class
                tableCircle.classList.add('skip-flash');

                // Remove the animation class after it completes
                setTimeout(() => {
                    tableCircle.classList.remove('skip-flash');
                }, 800);
            }

            // Remove the animation element after it completes
            setTimeout(() => {
                if (skipAnimation.parentNode === playerElement) {
                    skipAnimation.remove();
                }
            }, 1500);

            console.log("Skip animation added to player element:", playerElement);
        } else {
            console.error("Player element not found for position:", playerPosition);
        }
    }

    // Add a global variable to track system messages visibility state
    // Default to hidden (true) unless explicitly set to visible in localStorage
    let systemMessagesHidden = localStorage.getItem('systemMessagesHidden') !== 'false';

    // Initialize localStorage if it doesn't have a value yet
    if (localStorage.getItem('systemMessagesHidden') === null) {
        localStorage.setItem('systemMessagesHidden', 'true');
    }

    // Add a clear system messages button
    function addClearSystemMessagesButton() {
        // Check if button already exists
        if (document.getElementById('clear-system-messages')) {
            return;
        }

        // Create the button
        const clearButton = document.createElement('button');
        clearButton.id = 'clear-system-messages';
        clearButton.className = 'clear-system-btn';
        clearButton.innerHTML = systemMessagesHidden ? '🔊 Show System Messages' : '🔇 Hide System Messages';
        clearButton.title = systemMessagesHidden ? 'Show all system messages' : 'Hide all system messages';

        // Add active class if messages are hidden
        if (systemMessagesHidden) {
            clearButton.classList.add('active');
        }

        // Add click event
        clearButton.addEventListener('click', function () {
            const systemMessages = chatLog.querySelectorAll('.chat-message.system');
            systemMessagesHidden = !systemMessagesHidden;

            // Store preference in localStorage
            localStorage.setItem('systemMessagesHidden', systemMessagesHidden);

            if (systemMessagesHidden) {
                // Hide all system messages
                systemMessages.forEach(msg => {
                    msg.style.display = 'none';
                });
                this.classList.add('active');
                this.innerHTML = '🔊 Show System Messages';
                this.title = 'Show all system messages';
            } else {
                // Show all system messages
                systemMessages.forEach(msg => {
                    msg.style.display = '';
                });
                this.classList.remove('active');
                this.innerHTML = '🔇 Hide System Messages';
                this.title = 'Hide all system messages';
            }
        });

        // Add the button to the chat container, right after the header
        const chatHeader = document.querySelector('#chat-container h3');
        if (chatHeader) {
            chatHeader.parentNode.insertBefore(clearButton, chatHeader.nextSibling);
        }
    }

    // Call this function when the DOM is loaded
    addClearSystemMessagesButton();
}); 