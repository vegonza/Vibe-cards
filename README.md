# Vibe-Cards

A web-based multiplayer card game "Culo" built with Flask.

## Overview

Vibe-Cards is an implementation of the popular card game "Culo" that allows 2-4 players to play together in real-time. The game features a role system where players can be assigned different roles (President, Vice-President, Neutral, or Culo) based on their performance.

This is a fully vibe-coded project, where aesthetics and functionality blend together to create an immersive card game experience. By embracing the vibe coding philosophy, we've focused on creating a game that not only works well but feels good to play, with attention to visual design and user experience.

## Features

- Supports 2-4 players
- Real-time game updates
- Role system for tournament play
- Spectator mode for full games
- Responsive web interface
- Aesthetic-focused design elements
- Immersive gameplay experience

## Game Rules

1. **Basic Play:** Players must play a card of equal or higher value than the top card on the table, or skip their turn.
2. **Ace Power:** Playing an Ace clears the table and grants an extra turn.
3. **Two as Joker:** '2' cards can be played on any card and can represent any value.
4. **Same Value Skip:** Playing a card with the same value as the previous card skips the next player.
5. **Multiple Card Play:** Players can play multiple cards of the same value in a single turn.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the application:
   ```
   python app.py
   ```

3. Access the game at `http://localhost:5000`

## Technologies

- Backend: Flask
- Frontend: HTML, CSS, JavaScript
- Session Management: Flask sessions
- Vibe-Coding Philosophy: Blending aesthetics with functionality 