# Coolant module
from .module import Module

class CoolantModule(Module):

    def __init__(self, engine):
        super().__init__("coolant", engine) 

    def loadApp(self, app):
        print("Not yet implemented")