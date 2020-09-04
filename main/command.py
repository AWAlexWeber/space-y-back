# Command module
from .module import Module

class CommandModule(Module):

    def __init__(self, engine, resourceContainer):
        super().__init__("command", engine, resourceContainer) 

    def loadApp(self, app):
        print("Not yet implemented")