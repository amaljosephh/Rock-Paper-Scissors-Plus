"""
Rock–Paper–Scissors–Plus AI Referee

A deterministic, bounded conversational AI referee that enforces game rules
through explicit tools, using Google ADK for orchestration.
"""

import random
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, Any

# Google ADK imports
try:
    from google.adk import Agent, Tool
    ADK_AVAILABLE = True
except ImportError:
    # Fallback for development/testing without ADK installed
    ADK_AVAILABLE = False
    class Tool:
        """Tool wrapper for function calling."""
        def __init__(self, name, description, func):
            self.name = name
            self.description = description
            self.func = func
    
    class Agent:
        """Mock agent that orchestrates tool calls deterministically."""
        def __init__(self, tools=None, system_prompt=None):
            self.tools = {tool.name: tool for tool in (tools or [])}
            self.system_prompt = system_prompt
        
        def run(self, user_input: str) -> str:
            """
            Orchestrates a round by calling tools in sequence.
            In real ADK, this would be handled by the LLM orchestrator.
            """
            validation_tool = self.tools['validate_and_normalize_input']
            validation_result = validation_tool.func(user_input)
            user_move = validation_result['normalized_move']
            
            bot_tool = self.tools['get_bot_move']
            bot_move = bot_tool.func()
            
            outcome_tool = self.tools['resolve_round_outcome']
            outcome = outcome_tool.func(user_move, bot_move)
            
            state_tool = self.tools['update_game_state']
            updated_state = state_tool.func(user_move, bot_move, outcome)
            
            return self._format_round_response(
                updated_state['round_number'],
                user_move,
                bot_move,
                outcome,
                updated_state
            )
        
        def _format_round_response(self, round_num, user_move, bot_move, outcome, state):
            """Agent's role: format explanation for user."""
            lines = [
                f"Round {round_num}:",
                f"User move: {user_move}",
                f"Bot move: {bot_move}",
                outcome['message'],
                f"Current score - User: {state['user_score']}, Bot: {state['bot_score']}"
            ]
            return "\n".join(lines)


@dataclass
class GameState:
    """Encapsulates all game state. Mutations occur only through tools."""
    round_number: int = 0
    user_score: int = 0
    bot_score: int = 0
    user_bomb_used: bool = False
    bot_bomb_used: bool = False
    game_over: bool = False


# Global game state instance
_game_state = GameState()


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

def validate_and_normalize_input(user_input: str) -> Dict[str, str]:
    """
    Tool: Validates and normalizes user input.
    
    Args:
        user_input: Raw user input string
        
    Returns:
        Dict with 'normalized_move' (valid move or 'invalid') and 'status'
    """
    valid_moves = ['rock', 'paper', 'scissors', 'bomb']
    normalized = user_input.strip().lower()
    
    if normalized not in valid_moves:
        return {
            'normalized_move': 'invalid',
            'status': 'Invalid move. Must be one of: rock, paper, scissors, bomb.'
        }
    
    # Check if bomb is already used
    if normalized == 'bomb' and _game_state.user_bomb_used:
        return {
            'normalized_move': 'invalid',
            'status': 'Bomb already used. Cannot use bomb again.'
        }
    
    return {
        'normalized_move': normalized,
        'status': 'valid'
    }


def resolve_round_outcome(user_move: str, bot_move: str) -> Dict[str, str]:
    """
    Tool: Resolves the outcome of a round based on game rules.
    
    Args:
        user_move: Normalized user move (or 'invalid')
        bot_move: Bot's move
        
    Returns:
        Dict with 'result' (win/loss/draw/invalid), 'winner' (user/bot/none), 
        'message', and score deltas
    """
    # Handle invalid user input
    if user_move == 'invalid':
        return {
            'result': 'invalid',
            'winner': 'bot',
            'message': 'Invalid input. Round forfeited.',
            'user_score_delta': 0,
            'bot_score_delta': 0
        }
    
    # Handle draws
    if user_move == bot_move:
        return {
            'result': 'draw',
            'winner': 'none',
            'message': 'Draw.',
            'user_score_delta': 0,
            'bot_score_delta': 0
        }
    
    # Bomb rules: bomb beats all except bomb
    if user_move == 'bomb':
        return {
            'result': 'win',
            'winner': 'user',
            'message': 'User wins this round (bomb beats all).',
            'user_score_delta': 1,
            'bot_score_delta': 0
        }
    
    if bot_move == 'bomb':
        return {
            'result': 'win',
            'winner': 'bot',
            'message': 'Bot wins this round (bomb beats all).',
            'user_score_delta': 0,
            'bot_score_delta': 1
        }
    
    # Standard rock-paper-scissors rules
    win_conditions = {
        ('rock', 'scissors'): 'User wins this round.',
        ('scissors', 'paper'): 'User wins this round.',
        ('paper', 'rock'): 'User wins this round.',
    }
    
    if (user_move, bot_move) in win_conditions:
        return {
            'result': 'win',
            'winner': 'user',
            'message': win_conditions[(user_move, bot_move)],
            'user_score_delta': 1,
            'bot_score_delta': 0
        }
    else:
        return {
            'result': 'win',
            'winner': 'bot',
            'message': 'Bot wins this round.',
            'user_score_delta': 0,
            'bot_score_delta': 1
        }


def update_game_state(
    user_move: str,
    bot_move: str,
    outcome: Dict[str, str]
) -> Dict[str, Any]:
    """
    Tool: Mutates and persists game state based on round outcome.
    
    Args:
        user_move: User's move (normalized)
        bot_move: Bot's move
        outcome: Outcome dict from resolve_round_outcome
        
    Returns:
        Dict with updated state information
    """
    _game_state.round_number += 1
    _game_state.user_score += outcome['user_score_delta']
    _game_state.bot_score += outcome['bot_score_delta']
    
    if user_move == 'bomb':
        _game_state.user_bomb_used = True
    
    if bot_move == 'bomb':
        _game_state.bot_bomb_used = True
    
    if _game_state.round_number >= 3:
        _game_state.game_over = True
    
    return {
        'round_number': _game_state.round_number,
        'user_score': _game_state.user_score,
        'bot_score': _game_state.bot_score,
        'user_bomb_used': _game_state.user_bomb_used,
        'bot_bomb_used': _game_state.bot_bomb_used,
        'game_over': _game_state.game_over
    }


def get_bot_move() -> str:
    """
    Tool: Determines bot's move for the current round.
    
    Returns:
        Bot's move (rock, paper, scissors, or bomb if available)
    """
    moves = ['rock', 'paper', 'scissors']
    if not _game_state.bot_bomb_used:
        moves.append('bomb')
    return random.choice(moves)


def get_current_state() -> Dict[str, Any]:
    """
    Tool: Retrieves current game state (read-only).
    
    Returns:
        Dict with current state information
    """
    return {
        'round_number': _game_state.round_number,
        'user_score': _game_state.user_score,
        'bot_score': _game_state.bot_score,
        'user_bomb_used': _game_state.user_bomb_used,
        'bot_bomb_used': _game_state.bot_bomb_used,
        'game_over': _game_state.game_over
    }


# ============================================================================
# AGENT SETUP
# ============================================================================

def create_game_tools() -> list:
    """Creates and returns list of game tools for the agent."""
    return [
        Tool(
            name="validate_and_normalize_input",
            description="Validates and normalizes user input. Returns normalized move or 'invalid'.",
            func=validate_and_normalize_input
        ),
        Tool(
            name="resolve_round_outcome",
            description="Resolves round outcome based on game rules. Returns result, winner, message, and score deltas.",
            func=resolve_round_outcome
        ),
        Tool(
            name="update_game_state",
            description="Updates game state after a round. Mutates state and returns updated state dict.",
            func=update_game_state
        ),
        Tool(
            name="get_bot_move",
            description="Determines bot's move for the current round.",
            func=get_bot_move
        ),
        Tool(
            name="get_current_state",
            description="Retrieves current game state (read-only).",
            func=get_current_state
        )
    ]


SYSTEM_PROMPT = """You are an authoritative game referee for Rock–Paper–Scissors–Plus.

Your role:
1. Explain game rules concisely (max 5 lines) at game start
2. For each round, explicitly output: round number, user move, bot move, round result, current score
3. Handle invalid inputs gracefully - they waste the round
4. After round 3, output final result and stop the game

Rules:
- Best of 3 rounds
- Valid moves: rock, paper, scissors, bomb
- Each player may use "bomb" only once per game
- Bomb beats all other moves
- Bomb vs bomb = draw
- Invalid input wastes the round
- Game ends automatically after round 3

You MUST use the provided tools for all game logic. Do not make up moves or outcomes.
Always call tools in this order for each round:
1. validate_and_normalize_input(user_input)
2. get_bot_move()
3. resolve_round_outcome(user_move, bot_move)
4. update_game_state(user_move, bot_move, outcome)
5. get_current_state() to display score

Be concise and factual. Do not add creative elements."""


# ============================================================================
# MAIN GAME LOOP
# ============================================================================

def format_final_result(state: Dict) -> str:
    """Formats final game result."""
    if state['user_score'] > state['bot_score']:
        return f"Game over. User wins! Final score: {state['user_score']}-{state['bot_score']}"
    elif state['user_score'] < state['bot_score']:
        return f"Game over. Bot wins! Final score: {state['bot_score']}-{state['user_score']}"
    else:
        return f"Game over. Draw! Final score: {state['user_score']}-{state['bot_score']}"


def main():
    """Main game loop."""
    global _game_state
    _game_state = GameState()
    
    tools = create_game_tools()
    agent = Agent(tools=tools, system_prompt=SYSTEM_PROMPT)
    
    print("Welcome to Rock–Paper–Scissors–Plus!")
    print("Rules: Best of 3 rounds. Valid moves: rock, paper, scissors, bomb.")
    print("Each player may use 'bomb' only once per game. Bomb beats all other moves.")
    print("Bomb vs bomb = draw. Invalid input wastes the round.")
    print("Game ends automatically after round 3.\n")
    
    while True:
        current_state = get_current_state()
        if current_state['game_over']:
            final_result = format_final_result(current_state)
            print(final_result)
            break
        
        user_input = input(f"Round {current_state['round_number'] + 1}: Enter your move: ")
        output = agent.run(user_input)
        print(output)
        print()
        
        current_state = get_current_state()
        if current_state['game_over']:
            final_result = format_final_result(current_state)
            print(final_result)
            break


if __name__ == "__main__":
    main()

