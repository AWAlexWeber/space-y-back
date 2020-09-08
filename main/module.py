# Imports
from .log import Log
from auth.error import *
from .shipresourcecontainer import *

# Base module
class Module:

    def __init__(self, moduleName, engine, resourceContainer):
        self.moduleName = moduleName
        self.engine = engine
        self.status = "Offline"
        self.rebootTime = 6
        self.rebootStatus = False
        self.globalResourceContainer = resourceContainer
        self.internalResourceContainer = ShipResourceContainer(self.engine)

        # Dictionary by the sub modules FULL NAME (submodule_name-submodule_id ie reactor-1)
        self.subModules = {}

        # Starting the log
        self.log = Log(self.moduleName)
        self.log.appendLog("Initializing...")

    def getAdvancedStatus(self):
        return {}

    def addSubModule(self, subModule, name):
        self.subModules[name] = subModule

    def getSubModule(self, name):
        if name in self.subModules:
            return self.subModules[name]
        else:
            return None

    def online(self):

        # Onlining the module
        self.status = "Online"
        self.log.appendLog("Online", -1)

    def destroy(self):
        self.status = "Destroyed"

    def attemptDestroy(self):
        self.logParent("Destroyed!", 2)
        self.destroy()

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

    # Creating our resource pools
    def createResourcePools(self):
        # Set the resource pools to zero
        return None

    # Processing resource requests
    def processResourceAddToPool(self):
        # This will give out all the resources
        return None

    def processResourceRemoveFromPool(self):
        # This will take out resources
        return None

    # Extra processing
    def processExtra(self):
        return None

# Submodule
class SubModule:

    def __init__(self, subModuleName, subModuleId, parentModule, engine):
        self.name, self.id, self.parent, self.engine = subModuleName, subModuleId, parentModule, engine
        self.status = "Offline"

    def online(self):
        self.status = "Online"

    def offline(self):
        self.status = "Offline"

    def isOnline(self):
        return (True if self.status == "Online" else False)

    def logParent(self, message, type=0):
        self.parent.log.appendLog(str(self.name) + " (" + str(self.id) + ") - " + message, type)

    def attemptOnline(self):
        self.online()

        # Adding this to our module logs
        self.logParent("Online")
        return True

    def attemptOffline(self):
        self.offline()

        # Adding this to our module logs
        self.logParent("Offline")
        return True

    def destroy(self):
        self.status = "Destroyed"

    def attemptDestroy(self):
        self.logParent("Destroyed!", 2)
        self.destroy()

    def getAdvancedStatus(self):
        output = {}
        output["name"] = self.name
        output["id"] = self.id
        output["status"] = self.status
        return output