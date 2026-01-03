# Rock–Paper–Scissors–Plus AI Referee

A deterministic, bounded conversational AI referee implemented in Python using Google ADK. The system enforces game rules through explicit tools, ensuring state mutations occur only within tool boundaries.

## State Model

The `GameState` dataclass encapsulates all game state in a single, immutable-by-design structure:

- **round_number**: Current round (starts at 0, increments to 1-3 during gameplay)
- **user_score**: User's cumulative score
- **bot_score**: Bot's cumulative score
- **user_bomb_used**: Boolean flag indicating if user has used their bomb
- **bot_bomb_used**: Boolean flag indicating if bot has used their bomb
- **game_over**: Boolean flag indicating if game has ended (after round 3)

**Design Decision**: State is stored in a global `_game_state` instance to ensure persistence across tool calls. This choice simplifies tool access patterns while maintaining a single source of truth. All mutations occur exclusively within the `update_game_state` tool, creating a clear boundary that prevents the agent from directly modifying state. The dataclass structure provides type safety and makes the state model self-documenting.

## Agent/Tool Design

### ADK Primitives Usage

The implementation uses Google ADK's core primitives:
- **`Agent`**: The orchestrator that interprets user intent and coordinates tool calls
- **`Tool`**: Explicit function wrappers that enforce game boundaries
- **Structured Outputs**: All tools return typed dictionaries, enabling deterministic behavior

**Design Decision**: Tools are registered with the agent via `create_game_tools()`, which creates `Tool` instances with name, description, and function references. The agent's system prompt constrains it to use only these tools for game logic, preventing hallucination or rule-bending.

### Agent Role and Boundaries

The agent (orchestrated via Google ADK) has three distinct responsibilities with clear boundaries:

1. **Intent Understanding** (Agent's domain)
   - Interprets user input as a move attempt
   - Determines which tools to call and in what order
   - No game logic embedded here

2. **Game Logic** (Tool domain - agent cannot access)
   - Validation rules in `validate_and_normalize_input`
   - Win/loss determination in `resolve_round_outcome`
   - State mutation in `update_game_state`
   - Agent cannot bypass these tools or make up outcomes

3. **Response Generation** (Agent's domain)
   - Formats tool results into user-facing messages
   - Uses `_format_round_response` to structure output
   - No game logic, only presentation

**Boundary Enforcement**: The agent is constrained by a system prompt that mandates tool usage. In the mock implementation, `Agent.run()` demonstrates the expected orchestration pattern: it calls tools in sequence but never implements game logic directly.

### Tool Architecture

Five explicit tools enforce game boundaries:

1. **validate_and_normalize_input(user_input: str)**
   - Validates user input against valid moves
   - Checks bomb usage constraints
   - Returns normalized move or 'invalid' status
   - Pure function with no side effects

2. **resolve_round_outcome(user_move: str, bot_move: str)**
   - Implements deterministic game rules
   - Handles bomb logic (bomb beats all, bomb vs bomb = draw)
   - Returns outcome dict with winner, message, and score deltas
   - Pure function with no side effects

3. **update_game_state(user_move, bot_move, outcome)**
   - **Only state mutation point** in the system
   - Updates round number, scores, bomb flags
   - Sets game_over flag when round 3 completes
   - Returns updated state dict

4. **get_bot_move()**
   - Determines bot's move (random selection from available moves)
   - Respects bomb usage constraint
   - Returns bot's move string

5. **get_current_state()**
   - Read-only state accessor
   - Returns current state dict for display purposes

### Tool Call Sequence

For each round, tools are called in strict sequence:
1. `validate_and_normalize_input` → normalize user input
2. `get_bot_move` → determine bot move
3. `resolve_round_outcome` → compute round result
4. `update_game_state` → mutate state
5. `get_current_state` → retrieve state for display

This sequence ensures deterministic execution and prevents state inconsistencies.

## Tradeoffs

### Determinism vs. Randomness
- **Game logic**: Fully deterministic (rules are explicit)
- **Bot moves**: Randomized to simulate opponent unpredictability
- **Tradeoff**: Bot randomness introduces non-determinism, but game rules remain deterministic

### State Management
- **Global state**: Single global `_game_state` instance ensures persistence
- **Tool-based mutations**: All state changes occur in `update_game_state` tool
- **Tradeoff**: Global state simplifies tool access but requires careful mutation control

### Simplicity vs. Extensibility
- **Minimal dependencies**: Only Google ADK (with fallback mock for development)
- **Clear boundaries**: Explicit tool definitions enforce separation of concerns
- **Tradeoff**: Simple architecture limits complex features but ensures correctness

### Prompt Engineering
- **Constrained agent**: System prompt mandates tool usage
- **No embedded logic**: Game rules exist only in tool implementations
- **Tradeoff**: Agent cannot "cheat" by making up moves, but requires explicit tool orchestration

## Design Decisions Explained

### Why Global State?

**Decision**: Use a global `_game_state` instance rather than passing state through tool parameters.

**Rationale**: 
- Tools need read access to state for validation (e.g., checking if bomb was used)
- Passing state through every tool call would create coupling and make the API verbose
- Global state with single mutation point (`update_game_state`) maintains correctness
- For a single-game CLI, this is simpler than dependency injection

**Tradeoff**: Not thread-safe and doesn't support concurrent games, but acceptable for the specified use case.

### Why Separate Validation and Resolution?

**Decision**: Split input validation (`validate_and_normalize_input`) from outcome resolution (`resolve_round_outcome`).

**Rationale**:
- Clear separation of concerns: validation checks input, resolution checks game rules
- Allows invalid inputs to be handled gracefully (round still consumed)
- Makes testing easier (can test validation independently)
- Follows single responsibility principle

### Why Tool-Based State Mutation?

**Decision**: Only `update_game_state` can mutate state, even though other tools read it.

**Rationale**:
- Creates a single source of truth for state changes
- Prevents accidental mutations in validation or resolution logic
- Makes state transitions explicit and auditable
- Aligns with ADK's tool-based architecture pattern

## Possible Improvements

1. **Enhanced Input Parsing**
   - Support abbreviations (r, p, s, b)
   - Handle case variations and whitespace more robustly
   - Provide clearer error messages for invalid inputs

2. **State Persistence**
   - Serialize game state to file for session recovery
   - Support multiple concurrent games with state isolation

3. **Bot Strategy**
   - Implement non-random bot strategies (e.g., pattern detection, counter-strategies)
   - Add difficulty levels with different bot behaviors

4. **Testing**
   - Unit tests for each tool function
   - Integration tests for full game flows
   - Edge case coverage (bomb reuse, invalid inputs, draw scenarios)

5. **Error Handling**
   - More robust error handling for tool failures
   - Graceful degradation if ADK is unavailable
   - Input validation feedback before round execution

6. **Architecture**
   - Dependency injection for state management (remove global)
   - Tool registry pattern for dynamic tool discovery
   - Event-driven architecture for state change notifications

