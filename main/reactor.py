# Reactor module
import time
from .module import *

class ReactorModule(Module):

    def __init__(self, engine, resourceContainer):
        super().__init__("reactor", engine, resourceContainer) 

        # Loading in our reactor submodules
        self.reactorSubModules = list()
        for r in range(1,6):
            name = "reactor-"+str(r)
            powerOutput = 1000
            subModule = ReactorSubModule(r, self, self.engine, powerOutput)
            self.addSubModule(subModule, name)
            self.reactorSubModules.append(subModule)

    def loadApp(self, app):
        # Loading our reactor control points
        @app.route('/reactor/<path:id>/online', methods=['GET'])
        def online_reactor_sub_module(id):
            # Getting our engine status
            output = False
            name = 'reactor-' + str(id)
            reactorModule = self.getSubModule(name)

            if not reactorModule == None:
                output = reactorModule.attemptOnline()

            response = throw_json_success("Attempt to online reactor", output)
            return response

        @app.route('/reactor/<path:id>/offline', methods=['GET'])
        def offline_reactor_sub_module(id):
            # Getting our engine status
            output = False
            name = 'reactor-' + str(id)
            reactorModule = self.getSubModule(name)

            if not reactorModule == None:
                output = reactorModule.attemptOffline()

            response = throw_json_success("Attempt to online reactor", output)
            return response

        @app.route('/reactor/<path:id>/resources', methods=['GET'])
        def get_reactor_resource_levels(id):
            # Getting our engine status
            output = {}
            name = 'reactor-' + str(id)
            reactorModule = self.getSubModule(name)

            if not reactorModule == None:
                output = reactorModule.resourceContainer.getFullOutput()

            response = throw_json_success("Reator resources", output)
            return response

        @app.route('/reactor/all/resources', methods=['GET'])
        def get_all_reactor_resource_levels():
            # Getting our engine status
            output = {}

            for reactorSub in self.reactorSubModules:
                id = reactorSub.id
                output[id] = reactorSub.resourceContainer.getFullOutput()

            response = throw_json_success("Reator resources", output)
            return response

        @app.route('/reactor/all/statusAdvanced', methods=['GET'])
        def get_all_reactor_advanced_status():
            # Getting our engine status
            advancedStatusOutput = self.getAdvancedStatus()

            response = throw_json_success("Reator resources", output)
            return response

        @app.route('/reactor/<path:id>/refill', methods=['GET'])
        def enable_reactor_refill(id):
            # Getting our engine status
            output = False
            name = 'reactor-' + str(id)
            reactorModule = self.getSubModule(name)

            if not reactorModule == None:
                reactorModule.enableRefill()
                output = True

            response = throw_json_success("Enabling refill", output)
            return response

    # Getting advanced status
    def getAdvancedStatus(self):
        output = super().getAdvancedStatus()

        for reactorSub in self.reactorSubModules:
            id = reactorSub.id
            output[id] = reactorSub.getAdvancedStatus()

        return output

    # Creating our resource pools
    def createResourcePools(self):
        # Set the resource pools to zero
        self.resourceContainer.addResourceContainer("power", 500000)
        return None

    # Processing resource requests
    def processResourceAddToPool(self):
        # This will give out all the resources
        # Using our reactor submodules to deterine how much power to output
        for reactorSub in self.reactorSubModules:
            attemptPower = reactorSub.attempGeneratePower()
            self.resourceContainer.addResource("power", attemptPower)

            # Also, refilling the container if it has room
            if reactorSub.isRefill:
                reactorSub.refillOnce()

        return None

    def processResourceRemoveFromPool(self):
        # This will take out resources FROM THE POOL
        for reactorSub in self.reactorSubModules:
            # Attempting to draw power from
            if reactorSub.isOnline():
                attemptPower = reactorSub.attemptDrawFuel()

        return None

class ReactorSubModule(SubModule):

    def __init__(self, subModuleId, parentModule, engine, powerOutput):
        super().__init__("reactor", subModuleId, parentModule, engine)
        self.powerOutput = powerOutput
        self.pulledRequiredResource = False
        self.tritiumWarning = False
        self.deuteriumWarning = False
        self.tritiumUse = 30
        self.deuteriumUse = 20
        self.isRefill = False

        # Defining our own resource container for tritium and deuterium
        # Only use this for tritium and deuterium!
        self.resourceContainer = ShipResourceContainer(engine)
        self.resourceContainer.addResourceContainer("tritium", 1000)
        self.resourceContainer.addResourceContainer("deuterium", 1000)

    def getAdvancedStatus(self):
        data = super().getAdvancedStatus()
        data['resource'] = self.resourceContainer.getFullOutput()
        data['powerOutput'] = self.powerOutput
        return data

    def enableRefill(self):
        self.isRefill = True
        self.deuteriumWarning = False
        self.tritiumWarning = False

    def refillOnce(self):
        self.resourceContainer.addResource("tritium", 100)
        self.resourceContainer.addResource("deuterium", 100)

        # Are we at cap?
        resourceTritium, resourceDeuterium = self.resourceContainer.getResourceLevel("tritium"), self.resourceContainer.getResourceLevel("deuterium")
        if resourceTritium == self.resourceContainer.getResourceCap("tritium") and resourceDeuterium == self.resourceContainer.getResourceCap("deuterium"):
            self.isRefill = False

    # Function to draw fuel from our internal resource container
    # If it fails, set to false
    def attemptDrawFuel(self):
        # Only draw fuel when online
        if not self.isOnline():
            return

        # Do we have anything left?
        resourceTritium, resourceDeuterium = self.resourceContainer.getResourceLevel("tritium"), self.resourceContainer.getResourceLevel("deuterium")
        if resourceTritium <= 0 or resourceDeuterium <= 0:
            # If this is the first time, logging it so everyone knows that we fucked up
            if self.pulledRequiredResource:
                # Logging it
                self.logParent("Empty fuel tank!", 2)
            
            self.pulledRequiredResource = False


        else:
            self.pulledRequiredResource = True

            if not self.tritiumWarning and resourceTritium < self.resourceContainer.getResourceCap("tritium") / 2:
                self.logParent("50% Tritium", 2)
                self.tritiumWarning = True

            if not self.deuteriumWarning and resourceDeuterium < self.resourceContainer.getResourceCap("deuterium") / 2:
                self.logParent("50% Deuterium", 2)
                self.deuteriumWarning = True


        self.resourceContainer.removeResource("tritium", self.tritiumUse)
        self.resourceContainer.removeResource("deuterium", self.tritiumUse)


    def attempGeneratePower(self):
        if not self.isOnline():
            # Don't bother if we are in offline state
            return 0

        # Were we able to successfully pull in power last cycle?
        if self.pulledRequiredResource:
            # We did!
            # Let's output power
            return self.powerOutput
        
        # Finally, returning 0 if nothing else worked
        return 0