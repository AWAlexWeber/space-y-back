# Reactor module
from .module import Module

class OxyScrubModule(Module):

    def __init__(self, engine, resourceContainer):
        super().__init__("oxyscrub", engine, resourceContainer) 

    def loadApp(self, app):
        print("Not yet implemented")