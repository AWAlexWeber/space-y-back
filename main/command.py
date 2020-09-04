# Command module
from .module import Module

class CommandModule(Module):

    def __init__(self, engine):
        super().__init__("command", engine) 

    def loadApp(self, app):
        print("Not yet implemented")