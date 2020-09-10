# Coolant module
import time
import math
from .module import *
from .shipresourcecontainer import *

### SUB MODULES ###
COOLANT_DEUT_USE_RATE = 3
COOLANT_OXY_USE_RATE = 10
COOLANT_POWER_USE_RATE = 100

COOLANT_SUBMODULE_DEUTERIUM_MAX = 1000
COOLANT_SUBMODULE_OXYGEN_MAX = 10000
COOLANT_SUBMODULE_POWER_MAX = 5000

COOLANT_SUBMODULE_DEUT_REFIL_AMOUNT = 10
COOLANT_SUBMODULE_POWER_REFIL_RATE = 2000
COOLANT_SUBMODULE_OXY_REFIL_RATE = 1000

### MAIN ###
COOLANT_GENERATE_AMOUNT = 1.5
COOLANT_INTERNAL_OXY_MAX = 4000
COOLANT_INTERNAL_POWER_MAX = 50000

COOLANT_GLOBAL_COOLANT_MAX = 1000

class CoolantModule(Module):

    def __init__(self, engine, resourceContainer):
        super().__init__("coolant", engine, resourceContainer) 

        # Creating our internal resource pools
        self.internalResourceContainer.addResourceContainer("oxygen", COOLANT_INTERNAL_OXY_MAX)
        self.internalResourceContainer.addResourceContainer("power", COOLANT_INTERNAL_POWER_MAX)

        self.heatWarningTriggered = False
        self.heatErrorTriggered = False

        # Loading in our coolant submodules
        self.coolantSubModules = list()
        for r in range(1,6):
            name = "coolant-"+str(r)
            coolantOutput = COOLANT_GENERATE_AMOUNT
            subModule = CoolantSubModule(r, self, self.engine, coolantOutput)
            self.addSubModule(subModule, name)
            self.coolantSubModules.append(subModule)

    def loadApp(self, app):
        # Loading our coolant control points
        @app.route('/coolant/<path:id>/online', methods=['GET'])
        def online_coolant_sub_module(id):
            # Getting our engine status
            output = False
            name = 'coolant-' + str(id)
            coolantModule = self.getSubModule(name)

            if not coolantModule == None:
                output = coolantModule.attemptOnline()

            response = throw_json_success("Attempt to online coolant", output)
            return response

        @app.route('/coolant/<path:id>/offline', methods=['GET'])
        def offline_coolant_sub_module(id):
            # Getting our engine status
            output = False
            name = 'coolant-' + str(id)
            coolantModule = self.getSubModule(name)

            if not coolantModule == None:
                output = coolantModule.attemptOffline()

            response = throw_json_success("Attempt to online coolant", output)
            return response

        @app.route('/coolant/<path:id>/resources', methods=['GET'])
        def get_coolant_resource_levels(id):
            # Getting our engine status
            output = {}
            name = 'coolant-' + str(id)
            coolantModule = self.getSubModule(name)

            if not coolantModule == None:
                output = coolantModule.resourceContainer.getFullOutput()

            response = throw_json_success("coolant resources", output)
            return response

        @app.route('/coolant/all/resources', methods=['GET'])
        def get_all_coolant_resource_levels():
            # Getting our engine status
            output = {}

            for coolantSub in self.coolantSubModules:
                id = coolantSub.id
                output[id] = coolantSub.resourceContainer.getFullOutput()

            response = throw_json_success("coolant resources", output)
            return response

        @app.route('/coolant/all/statusAdvanced', methods=['GET'])
        def get_all_coolant_advanced_status():
            # Getting our engine status
            advancedStatusOutput = self.getAdvancedStatus()

            response = throw_json_success("Reator resources", advancedStatusOutput)
            return response

        @app.route('/coolant/<path:id>/refill', methods=['GET'])
        def enable_coolant_refill(id):
            # Getting our engine status
            output = False
            name = 'coolant-' + str(id)
            coolantModule = self.getSubModule(name)

            if not coolantModule == None:
                coolantModule.enableRefill()
                output = True

            response = throw_json_success("Enabling refill", output)
            return response

        @app.route('/coolant/<path:id>/override', methods=['GET'])
        def override_coolantr(id):
            output = False
            name = 'coolant-' + str(id)
            coolantModule = self.getSubModule(name)

            if not coolantModule == None:
                coolantModule.attemptDestroy()

        @app.route('/coolant/<path:id>/setSpin/<path:spinSpeed>/', methods=['GET'])
        def set_spin_speed(id, spinSpeed):
            output = False
            name = 'coolant-' + str(id)
            coolantModule = self.getSubModule(name)

            if not coolantModule == None:
                coolantModule.speed = int(spinSpeed)
                output = True

            response = throw_json_success("Set spin speed", output)
            return response

        # Getting advanced status
    def getAdvancedStatus(self):
        output = super().getAdvancedStatus()
        output["moduleOxygen"] = round(self.internalResourceContainer.getResourceLevel('oxygen') / self.internalResourceContainer.getResourceCap('oxygen') * 100)
        output["modulePower"] = round(self.internalResourceContainer.getResourceLevel('power') / self.internalResourceContainer.getResourceCap('power') * 100)
        output["resource"] = self.internalResourceContainer.getFullOutput()

        for coolantSub in self.coolantSubModules:
            id = coolantSub.id
            output[str(id)] = coolantSub.getAdvancedStatus()

        return output

    # Creating our resource pools
    def createResourcePools(self):
        # Set the resource pools to zero
        self.globalResourceContainer.addResourceContainer("coolant", COOLANT_GLOBAL_COOLANT_MAX)
        self.globalResourceContainer.addResource("coolant", 1000)
        
        return None

    # Processing resource requests
    def processResourceAddToPool(self):
        # This will give out all the resources
        # Using our coolant submodules to deterine how much power to output
        for coolantSub in self.coolantSubModules:
            # First, let's attempt to give the submodules coolant
            

            attemptCoolant = coolantSub.attemptGenerateCoolant()
            self.globalResourceContainer.addResource("coolant", attemptCoolant)

            # Attempting to add coolant to the individual reactor submodules
            if coolantSub.isOnline():
                drawPowerForCoolant = self.internalResourceContainer.removeResource('power', coolantSub.resourceContainer.getResourceCap('power') - coolantSub.resourceContainer.getResourceLevel('power'))
                coolantSub.resourceContainer.addResource('power', drawPowerForCoolant)

                drawOxygenForCoolant = self.internalResourceContainer.removeResource('oxygen', coolantSub.resourceContainer.getResourceCap('oxygen') - coolantSub.resourceContainer.getResourceLevel('oxygen'))
                coolantSub.resourceContainer.addResource('oxygen', drawOxygenForCoolant)

            # Also, refilling the container if it has room
            if coolantSub.isRefill:
                coolantSub.refillOnce()

        return None

    def processResourceRemoveFromPool(self):
        # This will take out resources FROM THE POOL
        for coolantSub in self.coolantSubModules:
            # Attempting to draw fuel
            if coolantSub.isOnline():
                coolantSub.attemptDrawFuel()

            # Attempting to draw coolant from the global coolant container into our internal one
            # Only draw how much we need to fill
            drawPower = self.globalResourceContainer.removeResource('power', self.internalResourceContainer.getResourceCap('power') - self.internalResourceContainer.getResourceLevel('power'), 'coolant')
            drawOxygen = self.globalResourceContainer.removeResource('oxygen', self.internalResourceContainer.getResourceCap('oxygen') - self.internalResourceContainer.getResourceLevel('oxygen'), 'coolant')
            self.internalResourceContainer.addResource('power', drawPower)
            self.internalResourceContainer.addResource('oxygen', drawOxygen)

        return None


class CoolantSubModule(SubModule):

    def __init__(self, subModuleId, parentModule, engine, coolantOutput):
        super().__init__("coolant", subModuleId, parentModule, engine)
        self.coolantOutput = coolantOutput
        self.pulledRequiredResource = False

        self.powerWarning = True
        self.oxygenWarning = True
        self.deuteriumWarning = True

        self.deuteriumUse = COOLANT_DEUT_USE_RATE
        self.oxygenUse = COOLANT_OXY_USE_RATE
        self.powerUse = COOLANT_POWER_USE_RATE
        self.isRefill = False
        self.speed = 1

        # Defining our own resource container for tritium and deuterium
        # Only use this for tritium and deuterium!
        self.resourceContainer = ShipResourceContainer(engine)
        self.resourceContainer.addResourceContainer("deuterium", COOLANT_SUBMODULE_DEUTERIUM_MAX)
        self.resourceContainer.addResourceContainer("oxygen", COOLANT_SUBMODULE_OXYGEN_MAX)
        self.resourceContainer.addResourceContainer("power", COOLANT_SUBMODULE_POWER_MAX)

    def getAdvancedStatus(self):
        data = super().getAdvancedStatus()
        data['resource'] = self.resourceContainer.getFullOutput()
        data['powerOutput'] = self.coolantOutput
        data['spinSpeed'] = self.speed
        return data

    def enableRefill(self):
        self.isRefill = True
        self.deuteriumWarning = False

    def refillOnce(self):
        self.resourceContainer.addResource("deuterium", COOLANT_SUBMODULE_DEUT_REFIL_AMOUNT)

        # Are we at cap?
        resourceDeuterium = self.resourceContainer.getResourceLevel("deuterium")
        if resourceDeuterium == self.resourceContainer.getResourceCap("deuterium"):
            self.isRefill = False

    # Function to draw fuel from our internal resource container
    # If it fails, set to false
    def attemptDrawFuel(self):
        # Only draw fuel when online
        if not self.isOnline():
            return

        # Do we have anything left?
        resourceOxygen, resourceDeuterium, resourcePower = self.resourceContainer.getResourceLevel("oxygen"), self.resourceContainer.getResourceLevel("deuterium"), self.resourceContainer.getResourceLevel("power")
        if resourceOxygen <= 0 or resourceDeuterium <= 0 or resourcePower <= 0:
            # If this is the first time, logging it so everyone knows that we fucked up
            if self.pulledRequiredResource:
                # Logging it
                self.logParent("Cannot generate coolant, missing resources!", 2)
            
            self.pulledRequiredResource = False


        else:
            self.pulledRequiredResource = True

            if not self.oxygenWarning and resourceOxygen < self.resourceContainer.getResourceCap("oxygen") / 2:
                self.logParent("50% Oxygen", 2)
                self.oxygenWarning = True
            elif self.oxygenWarning and resourceOxygen > self.resourceContainer.getResourceCap("oxygen") / 2:
                self.oxygenWarning = False
                self.logParent("More than 50% Oxygen", 0)

            if not self.powerWarning and resourcePower < self.resourceContainer.getResourceCap("power") / 2:
                self.logParent("50% Power", 2)
                self.powerWarning = True
            elif self.powerWarning and resourcePower > self.resourceContainer.getResourceCap("power") / 2:
                self.powerWarning = False
                self.logParent("More than 50% Power", 0)

            if not self.isRefill and not self.deuteriumWarning and resourceDeuterium < self.resourceContainer.getResourceCap("deuterium") / 2:
                self.logParent("50% Deuterium", 2)
                self.deuteriumWarning = True
            elif self.deuteriumWarning and resourceDeuterium > self.resourceContainer.getResourceCap("deuterium") / 2:
                self.deuteriumWarning = False
                self.logParent("More than 50% deuterium", 0)


        if self.pulledRequiredResource:
            self.resourceContainer.removeResource("power", self.powerUse * self.speed)
            self.resourceContainer.removeResource("oxygen", self.oxygenUse * self.speed)
            self.resourceContainer.removeResource("deuterium", self.deuteriumUse * self.speed)

    def attemptGenerateCoolant(self):
        if not self.isOnline():
            # Don't bother if we are in offline state
            return 0

        # Were we able to successfully pull in power last cycle?
        if self.pulledRequiredResource:
            # We did!

            # Let's output power
            return (self.coolantOutput * self.speed)
        
        # Finally, returning 0 if nothing else worked
        return 0