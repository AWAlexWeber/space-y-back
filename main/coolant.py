# Coolant module
from .module import Module

class CoolantModule(Module):

    def __init__(self, engine, resourceContainer):
        super().__init__("coolant", engine, resourceContainer) 

    def loadApp(self, app):
        print("Not yet implemented")