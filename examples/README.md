# Multi-Agent System Examples

This directory contains example implementations and flows demonstrating the multi-agent system capabilities.

## Agent Types

### Base Conversation Agent
- Handles user interaction and team assembly
- Creates project plans based on requirements
- Coordinates team formation

### Orchestrator Agent
- Manages task lists and goals
- Coordinates context streams between agents
- Handles agent pausing and resuming

### Specialized Agents
- Frontend Developer: UI/UX implementation
- Backend Developer: API and server logic
- Database Engineer: Schema design and optimization

### Support Agents
- Test Agent: Creates unit tests for changes
- Context Agent: Optimizes context between agents

## Example Flows

The `flows` directory contains example workflows demonstrating:
1. Project team setup
2. Task assignment and management
3. Inter-agent communication
4. Context optimization
5. Test coverage tracking

## Usage

```python
from examples.flows.example_project_flow import setup_project_team, example_workflow

# Set up a new project team
team = setup_project_team()

# Run example workflow
example_workflow()
```

## Agent Communication

Agents communicate through the orchestrator using context streams:
1. Each agent updates its context
2. Context agent optimizes and cleans context
3. Orchestrator manages context distribution
4. Test agent tracks changes and creates tests

## Error Handling

- Agents can be paused using orchestrator.pause_agent()
- Context optimization prevents context explosion
- Test coverage ensures quality
