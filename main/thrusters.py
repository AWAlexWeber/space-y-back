# Thrusters module
from .module import Module

class ThrusterModule(Module):

    def __init__(self, engine, resourceContainer):
        super().__init__("thrusters", engine, resourceContainer) 

    def loadApp(self, app):
        print("Not yet implemented")