from threading import Thread, Lock

# Resource queue, for accessing ship resources
class ShipResourceContainer:

    def __init__(self, engine):
        # Initializing the access data
        self.resourcePool = {}

        # Initializing the resource cap
        self.resourceCap = {}

        # Creating our resource lock
        self.mutex = Lock()

        # Ban list to prevent modules from taking a specific resource
        self.banList = {}

    def addToBanList(self, banModuleName, banResourceName):
        # If its not in the ban list, create a new one
        if banModuleName not in self.banList:
            self.banList[banModuleName] = {}
            self.banList[banModuleName][banResourceName] = True
        else:
            self.banList[banModuleName][banResourceName] = True

    def removeFromBanList(self, banModuleName, banResourceName):
        # Is this in our list?
        if banModuleName not in self.banList:
            return

        else:
            self.banList[banModuleName][banResourceName] = False

    def isInBanList(self, banModuleName, banResourceName):
        if banModuleName not in self.banList:
            return False

        elif banResourceName not in self.banList[banModuleName]:
            return False

        return self.banList[banModuleName][banResourceName]

    def getFullOutput(self):
        data = {}
        data['resourceLevels'] = self.getAllResourceLevels()
        data['resourceCaps'] = self.getAllResourceCaps()
        data['resourceBans'] = self.banList
        return data

    def getAllResourceLevels(self):
        return self.resourcePool

    def getAllResourceCaps(self):
        return self.resourceCap

    def getResourceLevel(self, resourceName):
        if resourceName in self.resourcePool:
            return self.resourcePool[resourceName]
        else:
            return 0

    def getResourceCap(self, resourceName):
        if resourceName in self.resourceCap:
            return self.resourceCap[resourceName]
        else:
            return 0

    def addResourceContainer(self, resourceName, resourceMaxAmount):
        self.resourceCap[resourceName] = resourceMaxAmount
        self.resourcePool[resourceName] = 0

    def addResource(self, resourceName, resourceAmount):
        self.mutex.acquire()
        try:
            if resourceName in self.resourcePool:
                finalAmount = resourceAmount + self.resourcePool[resourceName]

                if finalAmount > self.resourceCap[resourceName]:
                    finalAmount = self.resourceCap[resourceName]

                self.resourcePool[resourceName] = finalAmount

        finally:
             self.mutex.release()

             return

    # Directly setting the resource level
    # Use this cautiously
    def setResourceLevel(self, resourceName, resourceAmount):
        self.resourcePool[resourceName] = resourceAmount


    # Note that the request module allows us to 'ban' modules from getting resources
    # By default it is none, for if we want to avoid any bans
    def removeResource(self, resourceName, resourceAmount, requestModule=None):
        # Is this in our ban list?
        if self.isInBanList(requestModule, resourceName):
            return 0

        self.mutex.acquire()
        amountTaken = 0
        try:
            # Getting the data
            if resourceName in self.resourcePool:
                # Let's get the resource
                # Do we have enough, or are we scrapping the barrel?
                if self.resourcePool[resourceName] < resourceAmount:
                    # We take everything and return
                    amountTaken = self.resourcePool[resourceName]
                    self.resourcePool[resourceName] = 0
                else:
                    amountTaken = resourceAmount
                    self.resourcePool[resourceName] = self.resourcePool[resourceName] - resourceAmount
        finally:
            self.mutex.release()

            # Returning our resources
            return amountTaken
