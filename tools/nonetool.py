from tools.base import BaseTool

class NoneTool(BaseTool):
    name = "nonetool"
    description = '''
    A placeholder tool that does nothing.
    Returns a simple message indicating no action was taken.
    '''
    input_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }

    def execute(self, **kwargs) -> str:
        return "No action performed - this is a placeholder tool."