# Reactor module
import time
import math
from .module import *
from .shipresourcecontainer import *

### Main Reactor Varaibles ###
REACTOR_INTERNAL_HEAT_MAX = 500
REACTOR_INTERNAL_COOLANT_MAX = 500
REACTOR_GLOBAL_POWER_MAX = 500000

### Sub module Variables ###
REACTOR_SUBMODULE_GENERATE = 500   # RATE
REACTOR_SUBMODULE_TRITIUM_MAX = 1000
REACTOR_SUBMODULE_DEUTERIUM_MAX = 1000
REACTOR_SUBMODULE_COOLANT_MAX = 100
REACTOR_SUBMODULE_HEAT_MAX = 500

REACTOR_SUBMODULE_TRIT_REFIL_AMOUNT = 10.0   # RATE
REACTOR_SUBMODULE_DEUT_REFIL_AMOUNT = 10.0   # RATE

REACTOR_TRIT_USE_RATE = 2 # RATE
REACTOR_DEUT_USE_RATE = 3 # RATE

# Submodule heat #
REACTOR_SUBMODULE_COOLANT_REFIL_RATE = 2 # RATE
REACTOR_SUBMODULE_COOLANT_DRAW_AMOUNT = 1 # RATE
REACTOR_SUBMODULE_COOLANT_DRAW_HEAT_AMOUNT = 0.75 # RATE
REACTOR_SUBMODULE_HEAT_REMOVE_PASSIVE = 0.15 # RATE

REACTOR_HEAT_L1 = 50
REACTOR_HEAT_L2 = 80
REACTOR_HEAT_L3 = 100

# Additional gain ontop of default gain
REACTOR_HEAT_GAIN_DEFAULT = 0.5 # RATE
REACTOR_HEAT_GAIN_L1 = 0.75 # RATE
REACTOR_HEAT_GAIN_L2 = 0.5 # RATE
REACTOR_HEAT_GAIN_L3 = 0.25 # RATE

class ReactorModule(Module):

    def __init__(self, engine, resourceContainer):
        super().__init__("reactor", engine, resourceContainer) 

        # Creating our internal resource pools
        self.internalResourceContainer.addResourceContainer("coolant", REACTOR_INTERNAL_COOLANT_MAX)
        self.internalResourceContainer.addResourceContainer("heat", REACTOR_INTERNAL_HEAT_MAX)

        self.heatWarningTriggered = False
        self.heatErrorTriggered = False

        # Loading in our reactor submodules
        self.reactorSubModules = list()
        for r in range(1,6):
            name = "reactor-"+str(r)
            powerOutput = REACTOR_SUBMODULE_GENERATE
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

        @app.route('/reactor/<path:id>/override', methods=['GET'])
        def override_reactor(id):
            output = False
            name = 'reactor-' + str(id)
            reactorModule = self.getSubModule(name)

            if not reactorModule == None:
                reactorModule.attemptDestroy()

            response = throw_json_success("Blown up!", output)
            return response

    # Getting advanced status
    def getAdvancedStatus(self):
        output = super().getAdvancedStatus()
        output["moduleHeat"] = round(self.internalResourceContainer.getResourceLevel('heat'))
        output["moduleCoolant"] = round(self.internalResourceContainer.getResourceLevel('coolant') / self.internalResourceContainer.getResourceCap('coolant') * 100)

        for reactorSub in self.reactorSubModules:
            id = reactorSub.id
            output[str(id)] = reactorSub.getAdvancedStatus()

        return output

    # Creating our resource pools
    def createResourcePools(self):
        # Set the resource pools to zero
        self.globalResourceContainer.addResourceContainer("power", REACTOR_GLOBAL_POWER_MAX)
        
        return None

    # Processing resource requests
    def processResourceAddToPool(self):
        # This will give out all the resources
        # Using our reactor submodules to deterine how much power to output
        for reactorSub in self.reactorSubModules:
            # First, let's attempt to give the submodules coolant
            

            attemptPower = reactorSub.attempGeneratePower()
            self.globalResourceContainer.addResource("power", attemptPower)

            # Attempting to add coolant to the individual reactor submodules
            if reactorSub.isOnline():
                drawCoolantForReactor = self.internalResourceContainer.removeResource('coolant', REACTOR_SUBMODULE_COOLANT_REFIL_RATE)
                reactorSub.resourceContainer.addResource('coolant', drawCoolantForReactor)

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

            # No matter what, attempt to cool down
            reactorSub.attemptDissipateHeat()

            # Attempting to draw coolant from the global coolant container into our internal one
            # Only draw how much we need to fill
            drawnCoolant = self.globalResourceContainer.removeResource('coolant', self.internalResourceContainer.getResourceCap('coolant') - self.internalResourceContainer.getResourceLevel('coolant'), 'reactor')
            self.internalResourceContainer.addResource('coolant', drawnCoolant)

        return None

    def processExtra(self):
        super().processExtra()

        # Calculating our total internal heat
        totalHeat = 0
        for m in self.reactorSubModules:
            totalHeat += m.resourceContainer.getResourceLevel('heat')
        totalHeat = round(totalHeat / 5)

        self.internalResourceContainer.setResourceLevel('heat', totalHeat)

        if not self. heatWarningTriggered and totalHeat > 100:
            self.log.appendLog("Heat warning", 1)
            self.heatWarningTriggered = True
        
        if not self.heatErrorTriggered and totalHeat > 130:
            self.log.appendLog("Major Heat Error!", 2)
            self.heatErrorTriggered = True

        if self.heatWarningTriggered and totalHeat < 90:
            self.heatWarningTriggered = False
            self.log.appendLog("Heat not below 90", -1)

        if self.heatErrorTriggered and totalHeat < 110:
            self.heatErrorTriggered = False
            self.log.appendLog("Heat now below 110", 1)

class ReactorSubModule(SubModule):

    def __init__(self, subModuleId, parentModule, engine, powerOutput):
        super().__init__("reactor", subModuleId, parentModule, engine)
        self.powerOutput = powerOutput
        self.pulledRequiredResource = False
        self.tritiumWarning = False
        self.deuteriumWarning = False
        self.tritiumUse = REACTOR_TRIT_USE_RATE
        self.deuteriumUse = REACTOR_DEUT_USE_RATE
        self.isRefill = False

        # Defining our own resource container for tritium and deuterium
        # Only use this for tritium and deuterium!
        self.resourceContainer = ShipResourceContainer(engine)
        self.resourceContainer.addResourceContainer("tritium", REACTOR_SUBMODULE_TRITIUM_MAX)
        self.resourceContainer.addResourceContainer("deuterium", REACTOR_SUBMODULE_DEUTERIUM_MAX)
        self.resourceContainer.addResourceContainer("coolant", REACTOR_SUBMODULE_COOLANT_MAX)
        self.resourceContainer.addResourceContainer("heat", REACTOR_SUBMODULE_HEAT_MAX)

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
        self.resourceContainer.addResource("tritium", REACTOR_SUBMODULE_TRIT_REFIL_AMOUNT)
        self.resourceContainer.addResource("deuterium", REACTOR_SUBMODULE_DEUT_REFIL_AMOUNT)

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

            if not self.isRefill and not self.tritiumWarning and resourceTritium < self.resourceContainer.getResourceCap("tritium") / 2:
                self.logParent("50% Tritium", 2)
                self.tritiumWarning = True

            if not self.isRefill and not self.deuteriumWarning and resourceDeuterium < self.resourceContainer.getResourceCap("deuterium") / 2:
                self.logParent("50% Deuterium", 2)
                self.deuteriumWarning = True


        if self.pulledRequiredResource:
            self.resourceContainer.removeResource("tritium", self.tritiumUse)
            self.resourceContainer.removeResource("deuterium", self.deuteriumUse)

    def attemptDissipateHeat(self):
        # If we have coolant, we use 100 coolant units to dissipate 15
        if self.resourceContainer.getResourceLevel('coolant') > 0 and self.isOnline():
            self.resourceContainer.removeResource('coolant', REACTOR_SUBMODULE_COOLANT_DRAW_AMOUNT)
            self.resourceContainer.removeResource('heat', REACTOR_SUBMODULE_COOLANT_DRAW_HEAT_AMOUNT)

        # If we don't have any coolant, we use zero coolant to dissipate 3
        else:
            self.resourceContainer.removeResource('heat', REACTOR_SUBMODULE_HEAT_REMOVE_PASSIVE)

    def generateHeat(self):
        # Attempting to generate heat
        self.resourceContainer.addResource('heat', REACTOR_HEAT_GAIN_DEFAULT)

        # If our heat is less than 100%, we add an additional 10
        if (self.resourceContainer.getResourceLevel('heat') < REACTOR_HEAT_L1):
            self.resourceContainer.addResource('heat', REACTOR_HEAT_GAIN_L1)

        elif (self.resourceContainer.getResourceLevel('heat') < REACTOR_HEAT_L2):
            self.resourceContainer.addResource('heat', REACTOR_HEAT_GAIN_L2)

        elif (self.resourceContainer.getResourceLevel('heat') < REACTOR_HEAT_L3):
            self.resourceContainer.addResource('heat', REACTOR_HEAT_GAIN_L3)

    def attempGeneratePower(self):
        if not self.isOnline():
            # Don't bother if we are in offline state
            return 0

        # Were we able to successfully pull in power last cycle?
        if self.pulledRequiredResource:
            # We did!

            # First, let's generate heat
            self.generateHeat()

            # Let's output power
            return self.powerOutput
        
        # Finally, returning 0 if nothing else worked
        return 0