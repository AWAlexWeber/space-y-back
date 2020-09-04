# Reactor module
from .module import Module

class ReactorModule(Module):

    def __init__(self, engine):
        super().__init__("reactor", engine) 

    def loadApp(self, app):
        print("Not yet implemented")