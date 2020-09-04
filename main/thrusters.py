# Thrusters module
from .module import Module

class ThrusterModule(Module):

    def __init__(self, engine):
        super().__init__("thrusters", engine) 

    def loadApp(self, app):
        print("Not yet implemented")