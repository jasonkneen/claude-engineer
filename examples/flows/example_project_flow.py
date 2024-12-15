from examples.agents.base_conversation_agent import BaseConversationAgent, ConversationAgentRole
from examples.agents.orchestrator_agent import OrchestratorAgent, OrchestratorRole
from examples.agents.test_agent_example import TestAgent, TestAgentRole
from examples.agents.context_agent_example import ContextAgent, ContextAgentRole
from examples.agents.specialized_agents import FrontendAgent, BackendAgent, DatabaseAgent

def setup_project_team():
    """Example flow for setting up a project team"""
    # Initialize base conversation agent
    conversation_agent = BaseConversationAgent(
        agent_id="conv_1",
        role=ConversationAgentRole.PLANNER
    )

    # Create project plan based on requirements
    requirements = """
    Build a web application with:
    - User authentication
    - REST API backend
    - PostgreSQL database
    - React frontend
    """
    plan = conversation_agent.create_project_plan(requirements)

    # Initialize orchestrator
    orchestrator = OrchestratorAgent(
        agent_id="orch_1",
        role=OrchestratorRole.TASK_MANAGER
    )

    # Initialize specialized agents
    frontend_agent = FrontendAgent(agent_id="front_1")
    backend_agent = BackendAgent(agent_id="back_1")
    database_agent = DatabaseAgent(agent_id="db_1")

    # Initialize support agents
    test_agent = TestAgent(
        agent_id="test_1",
        role=TestAgentRole.UNIT_TESTER
    )
    context_agent = ContextAgent(
        agent_id="ctx_1",
        role=ContextAgentRole.OPTIMIZER
    )

    # Example task assignment
    tasks = [
        {
            "id": "task_1",
            "description": "Design database schema",
            "assigned_to": "db_1",
            "status": "pending"
        },
        {
            "id": "task_2",
            "description": "Implement authentication API",
            "assigned_to": "back_1",
            "status": "pending"
        },
        {
            "id": "task_3",
            "description": "Create login UI",
            "assigned_to": "front_1",
            "status": "pending"
        }
    ]

    # Register tasks with orchestrator
    for task in tasks:
        orchestrator.manage_task(
            task_id=task["id"],
            status=task["status"],
            agent_id=task["assigned_to"]
        )

    return {
        "conversation_agent": conversation_agent,
        "orchestrator": orchestrator,
        "specialized_agents": {
            "frontend": frontend_agent,
            "backend": backend_agent,
            "database": database_agent
        },
        "support_agents": {
            "test": test_agent,
            "context": context_agent
        }
    }

def example_workflow():
    """Example workflow demonstrating agent interactions"""
    team = setup_project_team()
    orchestrator = team["orchestrator"]

    # Example: Database agent starts working
    db_agent = team["specialized_agents"]["database"]
    schema_design = db_agent.design_schema({
        "entities": ["users", "sessions"],
        "relationships": ["user_sessions"]
    })

    # Test agent creates tests for schema
    test_agent = team["support_agents"]["test"]
    test_agent.create_test_case({
        "id": "schema_1",
        "file_path": "schema.sql",
        "description": "User and session schema implementation"
    })

    # Context agent optimizes context
    context_agent = team["support_agents"]["context"]
    context_agent.optimize_context({
        "schema": schema_design,
        "tests": test_agent.test_cases
    })

    # Update task status
    orchestrator.manage_task(
        task_id="task_1",
        status="completed",
        agent_id="db_1"
    )

if __name__ == "__main__":
    example_workflow()
