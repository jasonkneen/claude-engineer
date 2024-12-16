from tools.agent_base import AgentBaseTool, AgentRole
from tools.test_agent import TestAgentTool
from tools.context_manager import ContextManagerTool
from ce3 import Assistant

# Initialize the assistant to register our test agents
assistant = await Assistant.create()

# Create and register test agents
test_agent = TestAgentTool(agent_id='test_agent_1', role=AgentRole.TEST)
test_agent.start_task('Running test suite')
test_agent.update_progress(50)
assistant.tools.append(test_agent)

context_agent = ContextManagerTool(agent_id='context_agent_1', role=AgentRole.CONTEXT)
context_agent.start_task('Analyzing context streams')
context_agent.update_progress(75)
assistant.tools.append(context_agent)

print('Example agents created and registered with Assistant')
