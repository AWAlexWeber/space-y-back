# Reactor module
from .module import Module

OXYSCRUB_GLOBAL_OXYGEN_MAX = 100000

class OxyScrubModule(Module):

    def __init__(self, engine, resourceContainer):
        super().__init__("oxyscrub", engine, resourceContainer) 

    def loadApp(self, app):
        print("Not yet implemented")

    # Creating our resource pools
    def createResourcePools(self):
        # Set the resource pools to zero
        self.globalResourceContainer.addResourceContainer("oxygen", OXYSCRUB_GLOBAL_OXYGEN_MAX)
        self.globalResourceContainer.addResource("oxygen", 50000)
        
        return None