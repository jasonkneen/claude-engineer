class Assistant:
    def __init__(self):
        # Regular initialization
        self.tools = []
        self.initialized = False
        
    @classmethod
    async def create(cls):
        # Create instance
        instance = cls()
        # Do async initialization
        await instance.initialize()
        return instance
        
    async def initialize(self):
        # Put your async initialization code here
        self.initialized = True
