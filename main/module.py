# Imports
from .log import Log
from auth.error import *

# Base module
class Module:

    def __init__(self, moduleName, engine):
        self.moduleName = moduleName
        self.engine = engine
        self.status = "Offline"
        self.rebootTime = 6
        self.rebootStatus = False

        # Starting the log
        self.log = Log(self.moduleName)
        self.log.appendLog("Initializing...")

    def online(self):

        # Onlining the module
        self.status = "Online"
        self.log.appendLog("Online", -1)

    def attemptOnline(self):

        # Attempting to online the module
        # Generally want to override this
        self.online()
    
    def offline(self):
        
        # Offlining
        if self.status != "Offline":
            self.status = "Offline"
            self.log.appendLog("Offline", 2)

    def get_logs(self):
        # Returning all of the logs in list format
        return self.log.get_logs()

# Submodule
class SubModule:

    def __init__(self, subModuleName, subModuleId, parentModule, engine):
        self.name, self.id, self.parent, self.engine = subModuleName, subModuleId, parentModule, engine

    def online(self):
        this.status = "Online"

    def offline(self):
        this.status = "Offline"
