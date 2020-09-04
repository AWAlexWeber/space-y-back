# Reactor module
from .module import Module

class OxyScrubModule(Module):

    def __init__(self, engine):
        super().__init__("oxyscrub", engine) 

    def loadApp(self, app):
        print("Not yet implemented")