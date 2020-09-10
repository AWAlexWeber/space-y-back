# Thrusters module
from .module import Module

THRUSTER_INTERNAL_POWER_MAX = 10000
THRUSTER_INTERNAL_HEAT_MAX = 500
THRUSTER_INTERNAL_COOLANT_MAX = 1000

class ThrusterModule(Module):

    def __init__(self, engine, resourceContainer):
        super().__init__("thrusters", engine, resourceContainer) 
        self.internalResourceContainer.addResourceContainer("power", THRUSTER_INTERNAL_POWER_MAX)
        self.internalResourceContainer.addResourceContainer("heat", THRUSTER_INTERNAL_HEAT_MAX)
        self.internalResourceContainer.addResourceContainer("coolant", THRUSTER_INTERNAL_COOLANT_MAX)
        self.triggeredPowerWarning = True

        # Loading in our oxyscrub submodules
        self.thrusterModuleList = list()
        for r in range(1,5):
            name = "thruster-"+str(r)
            subModule = ThrusterSubModule(r, self, self.engine, oxyscrubOutput)
            self.addSubModule(subModule, name)
            self.thrusterModuleList.append(subModule)

    def loadApp(self, app):
        # Loading our oxyscrub control points
        @app.route('/oxyscrub/<path:id>/online', methods=['GET'])
        def online_oxyscrub_sub_module(id):
            # Getting our engine status
            output = False
            name = 'oxyscrub-' + str(id)
            subModule = self.getSubModule(name)

            if not subModule == None:
                output = subModule.attemptOnline()

            response = throw_json_success("Attempt to online oxyscrub", output)
            return response

        @app.route('/oxyscrub/<path:id>/offline', methods=['GET'])
        def offline_oxyscrub_sub_module(id):
            # Getting our engine status
            output = False
            name = 'oxyscrub-' + str(id)
            subModule = self.getSubModule(name)

            if not subModule == None:
                output = subModule.attemptOffline()

            response = throw_json_success("Attempt to offline oxyscrub", output)
            return response

        @app.route('/oxyscrub/<path:id>/resources', methods=['GET'])
        def get_oxyscrub_resource_levels(id):
            # Getting our engine status
            output = {}
            name = 'oxyscrub-' + str(id)
            subModule = self.getSubModule(name)

            if not subModule == None:
                output = subModule.resourceContainer.getFullOutput()

            response = throw_json_success("oxyscrub resources", output)
            return response

        @app.route('/oxyscrub/all/resources', methods=['GET'])
        def get_all_oxyscrub_resource_levels():
            # Getting our engine status
            output = {}

            for subModule in self.oxygenSubModules:
                id = subModule.id
                output[id] = subModule.resourceContainer.getFullOutput()

            response = throw_json_success("oxyscrub resources", output)
            return response

        @app.route('/oxyscrub/all/statusAdvanced', methods=['GET'])
        def get_all_oxyscrub_advanced_status():
            # Getting our engine status
            advancedStatusOutput = self.getAdvancedStatus()

            response = throw_json_success("Oxyscrub all", advancedStatusOutput)
            return response

        @app.route('/oxyscrub/<path:id>/override', methods=['GET'])
        def override_oxyscrubr(id):
            output = False
            name = 'oxyscrub-' + str(id)
            subModule = self.getSubModule(name)

            if not subModule == None:
                subModule.attemptDestroy()

        @app.route('/oxyscrub/<path:id>/newFilter/<path:filterId>/<path:filter>/', methods=['GET'])
        def replace_filter(id, filterId, filter):
            output = False
            name = 'oxyscrub-' + str(id)
            oxyscrubModule = self.getSubModule(name)

            correctNewFilter = ""
            if not oxyscrubModule == None:
                correctNewFilter = oxyscrubModule.filterList[int(filterId)].calculateNewTitle()
                output = oxyscrubModule.filterList[int(filterId)].attemptReplaceFilter(filter)

            response = throw_json_success("New filter, compared against " + str(correctNewFilter), output)
            return response

    # Processing resource requests
    def processResourceAddToPool(self):
        # This will give out all the resources
        # Using our oxyscrub submodules to deterine how much power to output
        for oxyscrubSub in self.oxygenSubModules:
            # First, let's attempt to give the submodules oxyscrub
            

            attemptOxygen = oxyscrubSub.attemptGenerateOxygen()
            self.globalResourceContainer.addResource("oxygen", attemptOxygen)

            # Attempting to add oxyscrub to the individual reactor submodules
            if oxyscrubSub.isOnline():
                drawPower = self.internalResourceContainer.removeResource('power', oxyscrubSub.resourceContainer.getResourceCap('power') - oxyscrubSub.resourceContainer.getResourceLevel('power'))
                oxyscrubSub.resourceContainer.addResource('power', drawPower)

        return None

    def processResourceRemoveFromPool(self):
        # This will take out resources FROM THE POOL

        # No matter what, people gotta breath
        self.globalResourceContainer.removeResource('oxygen', BREATH_RATE)

        for oxyscrubSub in self.oxygenSubModules:
            # Attempting to draw fuel
            if oxyscrubSub.isOnline():
                oxyscrubSub.attemptDrawFuel()

            # Attempting to draw oxyscrub from the global oxyscrub container into our internal one
            # Only draw how much we need to fill
            drawPower = self.globalResourceContainer.removeResource('power', self.internalResourceContainer.getResourceCap('power') - self.internalResourceContainer.getResourceLevel('power'), 'oxyscrub')
            self.internalResourceContainer.addResource('power', drawPower)

        return None

    # Creating our resource pools
    def createResourcePools(self):
        # Set the resource pools to zero
        self.globalResourceContainer.addResourceContainer("oxygen", OXYSCRUB_GLOBAL_OXYGEN_MAX)
        self.globalResourceContainer.addResource("oxygen", OXYSCRUB_GLOBAL_OXYGEN_MAX)
        
        return None

    def getAdvancedStatus(self):
        output = super().getAdvancedStatus()
        output["resource"] = self.internalResourceContainer.getFullOutput()

        for oxyscrub in self.oxygenSubModules:
            id = oxyscrub.id
            output[str(id)] = oxyscrub.getAdvancedStatus()

        return output

class ThrusterSubModule(SubModule):

    def __init__(self, subModuleId, parentModule, engine, oxygenOutput):
        super().__init__("oxyscrub", subModuleId, parentModule, engine)
        self.pulledRequiredResource = False
        self.powerWarning = True
        self.powerUse = OXYSCRUB_POWER_USE_RATE

        self.resourceContainer = ShipResourceContainer(engine)
        self.resourceContainer.addResourceContainer("power", OXYSCRUB_SUBMODULE_POWER_MAX)

        # Creating all our filters
        self.filterList = [None] * 2
        for i in range(0, 2):
            self.filterList[i] = OxyScrubFilter(i)

    def getAdvancedStatus(self):
        data = super().getAdvancedStatus()
        data['filterLevel'] = self.calculateTotalFilterLevel()
        for filter in self.filterList:
            id = filter.id
            data['filter-' + str(id)] = filter.getAdvancedStatus()
        data['resource'] = self.resourceContainer.getFullOutput()
        return data

    def calculateTotalFilterLevel(self):
        filterOutput = 0
        for filter in self.filterList:
            filterOutput += filter.filtrationLevel
        return round(filterOutput / 2)

    def attemptDrawFuel(self):
        # Only draw fuel when online
        if not self.isOnline():
            return

        # Do we have anything left?
        resourcePower = self.resourceContainer.getResourceLevel("power")
        if resourcePower <= 0:
            # If this is the first time, logging it so everyone knows that we fucked up
            if self.pulledRequiredResource:
                # Logging it
                self.logParent("Cannot generate oxygen, missing power!", 2)
            
            self.pulledRequiredResource = False


        else:
            self.pulledRequiredResource = True

            if not self.powerWarning and resourcePower < self.resourceContainer.getResourceCap("power") / 2:
                self.logParent("50% Power", 2)
                self.powerWarning = True

            else:
                self.powerWarning = False

        if self.pulledRequiredResource:
            self.resourceContainer.removeResource("power", self.powerUse)

    def attemptGenerateOxygen(self):
        if not self.isOnline():
            # Don't bother if we are in offline state
            return 0

        # Were we able to successfully pull in power last cycle?
        if self.pulledRequiredResource:
            # We did!

            # Calculating the total oxygen output based off of the efficiency of each filter
            filterEfficiency = 0
            for filter in self.filterList:
                filterEfficiency += filter.filtrationLevel
                filter.degradeFilter()
            filterEfficiency = filterEfficiency / 2

            # Let's output power
            return ((filterEfficiency / 100) * OXYSCRUB_MAX_RATE_GENERATE)
        
        # Finally, returning 0 if nothing else worked
        return 0