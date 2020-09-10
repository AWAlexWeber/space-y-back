# Thrusters module
import time
import random
import math
from .module import *
import string
from .shipresourcecontainer import *

THRUSTER_INTERNAL_POWER_MAX = 10000
THRUSTER_INTERNAL_HEAT_MAX = 500
THRUSTER_INTERNAL_COOLANT_MAX = 1000

# 4 'main' thrusters, so 4xup_max gives us the amount we go up by
THRUSTER_UP_MAX = 100
THRUSTER_GRAVITY_FORCE = 300 #m/s
THRUSTER_UP_MIN = 50

# Module use amount
THRUSTER_POWER_USE = 200
THRUSTER_COOLANT_USE = 1

# Submodule heat #
THRUSTER_SUBMODULE_COOLANT_REFIL_RATE = 2 # RATE
THRUSTER_SUBMODULE_COOLANT_DRAW_AMOUNT = 1 # RATE
THRUSTER_SUBMODULE_COOLANT_DRAW_HEAT_AMOUNT = 0.75 # RATE
THRUSTER_SUBMODULE_HEAT_REMOVE_PASSIVE = 0.15 # RATE

THRUSTER_HEAT_L1 = 50
THRUSTER_HEAT_L2 = 80
THRUSTER_HEAT_L3 = 100

# Additional gain ontop of default gain
THRUSTER_HEAT_GAIN_DEFAULT = 0.5 # RATE
THRUSTER_HEAT_GAIN_L1 = 0.75 # RATE
THRUSTER_HEAT_GAIN_L2 = 0.5 # RATE
THRUSTER_HEAT_GAIN_L3 = 0.25 # RATE

THRUSTER_MASTER_ANGLE_MOVE_RATE = 0.1

class ThrusterModule(Module):

    def __init__(self, engine, resourceContainer):
        super().__init__("thrusters", engine, resourceContainer) 
        self.internalResourceContainer.addResourceContainer("power", THRUSTER_INTERNAL_POWER_MAX)
        self.internalResourceContainer.addResourceContainer("heat", THRUSTER_INTERNAL_HEAT_MAX)
        self.internalResourceContainer.addResourceContainer("coolant", THRUSTER_INTERNAL_COOLANT_MAX)
        self.triggeredPowerWarning = True

        self.controlAngle = 0

        # Loading in our thruster submodules
        self.thrusterModuleList = list()
        for r in range(1,5):
            name = "thruster-"+str(r)
            subModule = ThrusterSubModule(r, self, self.engine)
            self.addSubModule(subModule, name)
            self.thrusterModuleList.append(subModule)

    # Creating our resource pools
    def createResourcePools(self):
        # Set the maximum altitude container up
        self.globalResourceContainer.addResourceContainer("altitude", 500000)
        self.globalResourceContainer.setResourceLevel("altitude", 150000)
        
        return None

    def getAdvancedStatus(self):
        output = super().getAdvancedStatus()
        output["resource"] = self.internalResourceContainer.getFullOutput()
        output['controlAngle'] = self.controlAngle

        for thrusterSub in self.thrusterModuleList:
            id = thrusterSub.id
            output[str(id)] = thrusterSub.getAdvancedStatus()

        return output

    # Processing resource requests
    def processResourceAddToPool(self):
        # This will give out all the resources
        # Using our reactor submodules to deterine how much power to output
        for thrusterSub in self.thrusterModuleList:

            # First, let's attempt to give the submodules coolant
            attemptUpwardForce = thrusterSub.attemptGenerateThrust()
            self.globalResourceContainer.addResource("altitude", attemptUpwardForce)

        return None

    def processResourceRemoveFromPool(self):
        # This will take out resources FROM THE POOL
        # Drop due to gravity
        if self.engine.IS_GAME_ENABLED:
            self.globalResourceContainer.removeResource("altitude", THRUSTER_GRAVITY_FORCE)

        for thrusterSub in self.thrusterModuleList:
            # Attempting to draw power from
            if thrusterSub.isOnline():
                thrusterSub.attemptDrawFuel()

            # No matter what, attempt to cool down
            thrusterSub.attemptDissipateHeat()

            # Attempting to draw coolant from the global coolant container into our internal one
            # Only draw how much we need to fill
            drawnCoolant = self.globalResourceContainer.removeResource('coolant', self.internalResourceContainer.getResourceCap('coolant') - self.internalResourceContainer.getResourceLevel('coolant'), 'thruster')
            self.internalResourceContainer.addResource('coolant', drawnCoolant)

            drawnPower = self.globalResourceContainer.removeResource('power', self.internalResourceContainer.getResourceCap('power') - self.internalResourceContainer.getResourceLevel('power'), 'thruster')
            self.internalResourceContainer.addResource('power', drawnPower)

        return None

    def processExtra(self):
        super().processExtra()

        if self.controlAngle % 90 > self.controlAngle + THRUSTER_MASTER_ANGLE_MOVE_RATE % 90:
            self.log.appendLog("Master Angle Swap", 1)

        if self.engine.IS_GAME_ENABLED:
            self.controlAngle += THRUSTER_MASTER_ANGLE_MOVE_RATE
            if self.controlAngle > 360:
                self.controlAngle = 0

    def loadApp(self, app):
        # Loading our thruster control points
        @app.route('/thrusters/<path:id>/online', methods=['GET'])
        def online_thruster_sub_module(id):
            # Getting our engine status
            output = False
            name = 'thruster-' + str(id)
            subModule = self.getSubModule(name)

            if not subModule == None:
                output = subModule.attemptOnline()

            response = throw_json_success("Attempt to online thruster", output)
            return response

        @app.route('/thrusters/<path:id>/offline', methods=['GET'])
        def offline_thruster_sub_module(id):
            # Getting our engine status
            output = False
            name = 'thruster-' + str(id)
            subModule = self.getSubModule(name)

            if not subModule == None:
                output = subModule.attemptOffline()

            response = throw_json_success("Attempt to offline thruster", output)
            return response

        @app.route('/thrusters/<path:id>/resources', methods=['GET'])
        def get_thruster_resource_levels(id):
            # Getting our engine status
            output = {}
            name = 'thruster-' + str(id)
            subModule = self.getSubModule(name)

            if not subModule == None:
                output = subModule.resourceContainer.getFullOutput()

            response = throw_json_success("thruster resources", output)
            return response

        @app.route('/thrusters/all/resources', methods=['GET'])
        def get_all_thruster_resource_levels():
            # Getting our engine status
            output = {}

            for subModule in self.thrusterModuleList:
                id = subModule.id
                output[id] = subModule.resourceContainer.getFullOutput()

            response = throw_json_success("thruster resources", output)
            return response

        @app.route('/thrusters/all/statusAdvanced', methods=['GET'])
        def get_all_thruster_advanced_status():
            # Getting our engine status
            advancedStatusOutput = self.getAdvancedStatus()

            response = throw_json_success("thruster all", advancedStatusOutput)
            return response

        @app.route('/thrusters/<path:id>/override', methods=['GET'])
        def override_thrusterr(id):
            output = False
            name = 'thruster-' + str(id)
            subModule = self.getSubModule(name)

            if not subModule == None:
                subModule.attemptDestroy()

            response = throw_json_success("thruster destroyed", output)
            return response

        @app.route('/thrusters/setMode/<path:mode>', methods=['GET'])
        def set_thrusters_mode(mode):
            output = False
            for thruster in self.thrusterModuleList:
                thruster.thrusterMode = mode

            response = throw_json_success("set thruster mode", output)
            return response

        @app.route('/thrusters/skipNextAngle/', methods=['GET'])
        def skip_to_next_thruster_angle():
            output = False

            self.controlAngle = self.controlAngle + 90
            self.controlAngle = round(self.controlAngle / 90)
            self.controlAngle = self.controlAngle * 90

            response = throw_json_success("set thruster mode", output)
            return response

class ThrusterSubModule(SubModule):

    def __init__(self, subModuleId, parentModule, engine):
        super().__init__("thruster", subModuleId, parentModule, engine)
        self.pulledRequiredResource = False
        
        self.powerWarning = True
        self.heatWarning = True
        self.coolantWarning = True

        self.thrusterAngle = 0
        self.thrusterMode = 'Low'

    def getAdvancedStatus(self):
        data = super().getAdvancedStatus()
        data['thrusterAngle'] = self.thrusterAngle
        data['thrusterMode'] = self.thrusterMode

        return data

    def attemptDrawFuel(self):
        # Only draw fuel when online
        if not self.isOnline():
            return

        # Do we have anything left?
        resourceContainer = self.parent.internalResourceContainer
        resourcePower = resourceContainer.getResourceLevel("power")
        if resourcePower <= 0:
            # If this is the first time, logging it so everyone knows that we fucked up
            if self.pulledRequiredResource:
                # Logging it
                self.logParent("No more power!", 2)
            
            self.pulledRequiredResource = False


        else:
            self.pulledRequiredResource = True

            if not self.powerWarning and resourcePower < resourceContainer.getResourceCap("power") / 2:
                self.logParent("50% Power", 2)
                self.powerWarning = True
            elif self.powerWarning and resourcePower > resourceContainer.getResourceCap("power") / 2:
                self.powerWarning = False
                self.logParent("More than 50% power", 0)


        if self.pulledRequiredResource:
            if (self.thrusterMode == 'High'):
                resourceContainer.removeResource("power", 2 * THRUSTER_POWER_USE)
            else:
                resourceContainer.removeResource("power", THRUSTER_POWER_USE)


    def attemptDissipateHeat(self):
        # If we have coolant, we use 100 coolant units to dissipate 15
        resourceContainer = self.parent.internalResourceContainer
        if resourceContainer.getResourceLevel('coolant') > 0 and self.isOnline():
            resourceContainer.removeResource('coolant', THRUSTER_SUBMODULE_COOLANT_DRAW_AMOUNT)
            resourceContainer.removeResource('heat', THRUSTER_SUBMODULE_COOLANT_DRAW_HEAT_AMOUNT)

        # If we don't have any coolant, we use zero coolant to dissipate 3
        else:
            resourceContainer.removeResource('heat', THRUSTER_SUBMODULE_HEAT_REMOVE_PASSIVE)

    def generateHeat(self):
        # Attempting to generate heat
        resourceContainer = self.parent.internalResourceContainer
        resourceContainer.addResource('heat', THRUSTER_HEAT_GAIN_DEFAULT)

        # If our heat is less than 100%, we add an additional 10
        if (resourceContainer.getResourceLevel('heat') < THRUSTER_HEAT_L1):
            resourceContainer.addResource('heat', THRUSTER_HEAT_GAIN_L1)

        elif (resourceContainer.getResourceLevel('heat') < THRUSTER_HEAT_L2):
            resourceContainer.addResource('heat', THRUSTER_HEAT_GAIN_L2)

        elif (resourceContainer.getResourceLevel('heat') < THRUSTER_HEAT_L3):
            resourceContainer.addResource('heat', THRUSTER_HEAT_GAIN_L3)

    def attemptGenerateThrust(self):
        if not self.isOnline():
            # Don't bother if we are in offline state
            return 0

        # Were we able to successfully pull in power last cycle?
        if self.pulledRequiredResource:
            # We did!

            # First, let's generate heat
            self.generateHeat()

            # Let's output power
            if self.thrusterMode == 'Low':
                return THRUSTER_UP_MIN
            else:
                return THRUSTER_UP_MAX
        
        # Finally, returning 0 if nothing else worked
        return 0