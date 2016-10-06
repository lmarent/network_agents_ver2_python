class AgentType():

    CONSUMER_TYPE = 1 
    PROVIDER_ISP = 2 
    PROVIDER_BACKHAUL = 3
    PRESENTER_TYPE = 4
    PROVIDER_SUP = 5
    
    def __init__(self, type):
        self.intfNames = {}    
        self.intfNames[AgentType.CONSUMER_TYPE] = 'consumer'
        self.intfNames[AgentType.PROVIDER_ISP] = 'provider'
        self.intfNames[AgentType.PROVIDER_BACKHAUL] = 'provider'
        self.intfNames[AgentType.PRESENTER_TYPE] = 'presenter'
        self.intfNames[AgentType.PROVIDER_SUP] = 'provider'
        self.value = type
        
    def getInterfaceName(self):
        return self.intfNames[self.value]

    def getType(self):
        return self.value