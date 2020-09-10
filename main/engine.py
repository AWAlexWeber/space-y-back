# Performing imports

# Importing modules
from .command import CommandModule
from .log import Log
from .module import Module
from .coolant import CoolantModule
from .oxyscrub import OxyScrubModule
from .reactor import ReactorModule
from .thrusters import ThrusterModule
from .eventqueue import EventSystem, Event

from .module import *

# Importing base
from auth.error import *
import requests
import datetime  
import datetime
import time

# Getting the flask request object
from flask import request

# Main engine script
class Engine:

    def __init__(self, app):
        # Starting up the engine
        self.status = "Offline"

        # Creating the modules list
        self.modules = list()
        self.modulesTable = {}
        self.app = app

        # Starting the onlining process
        self.status = "Onlining"

        # Meeting data
        self.meetingMode = False
        self.meetingStartTime = None
        self.totalMeetingAdjustTimeMS = 0

        # Enabling the clock module
        self.startTime = datetime.datetime.now() 

        # Starting our own internal logging system
        self.log = Log("Engine")
        self.log.appendLog("Starting engine", 0)

        # Starting our event system
        self.eventSystem = EventSystem()
        self.IS_GAME_ENABLED = False

        # Starting our resource pool
        resourcePool = ShipResourceContainer(self)
        self.resourcePool = resourcePool

        # Onling bare-bones stuff
        admin = AdminModule(self, resourcePool)
        admin.online()

        self.modules.append(admin)

        credentials = CredentialsApp(self, resourcePool)
        credentials.online()

        self.modules.append(credentials)

        # Loading them in
        self.modules.append(CommandModule(self, resourcePool))
        self.modules.append(CoolantModule(self, resourcePool))
        self.modules.append(OxyScrubModule(self, resourcePool))
        self.modules.append(ReactorModule(self, resourcePool))
        self.modules.append(ThrusterModule(self, resourcePool))

        # Initializing the modules resource requests pools
        # Basically we allow them to initialzie their own access pools
        for module in self.modules:
            # Starting their resource pools
            module.createResourcePools()

        # Loading in our modules
        self.loadApp(self.app)
        for m in self.modules:
            m.loadApp(self.app)
            self.modulesTable[m.moduleName] = m

        # Indicating we've completed our online process
        self.status = "Online"

    # Loading the application
    def loadApp(self, app):

        # Handling meetings
        @app.route('/engine/meeting/start', methods=['GET'])
        def start_meeting():
            if (self.meetingMode):
                response = throw_json_success("Already in meeting", False)
                return response

            self.meetingMode = True
            self.meetingStartTime = datetime.datetime.now()

            response = throw_json_success("Meeting started", True)
            return response

        @app.route('/engine/meeting/end', methods=['GET'])
        def end_meeting():
            if (not self.meetingMode):
                response = throw_json_success("No active meeting to adjourn", False)
                return response


            self.meetingMode = False
            self.totalMeetingAdjustTimeMS = self.totalMeetingAdjustTimeMS + (datetime.datetime.now() - self.meetingStartTime).microseconds // 100
            self.meetingStartTime = None

            response = throw_json_success("Meeting adjourned", True)
            return response

        # Initializing our engine routes
        @app.route('/engine/startGame', methods=['GET'])
        def start_game():
            # Getting our engine status
            self.IS_GAME_ENABLED = True

            response = throw_json_success("Started game!", True)
            return response

        # Initializing our engine routes
        @app.route('/engine/stopGame', methods=['GET'])
        def stop_game():
            # Getting our engine status
            self.IS_GAME_ENABLED = False

            response = throw_json_success("Stopped game!", True)
            return response

        # Initializing our engine routes
        @app.route('/engine/status', methods=['GET'])
        def get_engine_status():
            # Getting our engine status
            data = self.getSystemsStatus()

            response = throw_json_success("Engine Status", data)
            return response

        @app.route('/engine/statusAdvanced', methods=['GET'])
        def get_status_advanced():
            start = time.time()
            # Getting all status information for the engine
            output = {}
            output['time'] = self.getTime()
            output['reboot'] = self.getRebootInfo()
            output['status'] = self.getSystemsStatus()
            output['logs'] = self.get_system_logs()
            output['resource'] = self.getResourceLevels()
            output['meeting'] = self.getMeetingData()
            end = time.time()
            print(f"Runtime of the program is {end - start}")

            return throw_json_success("Advanced System Status", output)
            
        @app.route('/engine/statusAdvancedAll', methods=['GET'])
        def get_status_everything():

            # Getting all status information for the engine
            output = {}
            output['time'] = self.getTime()
            output['reboot'] = self.getRebootInfo()
            output['status'] = self.getSystemsStatus()
            output['logs'] = self.get_system_logs()
            output['resource'] = self.getResourceLevels()
            output['meeting'] = self.getMeetingData()
            module_output = {}

            # Getting all of the current modules
            for module_name in self.modulesTable:
                module_output[module_name] = self.modulesTable[module_name].getAdvancedStatus()
            output['modules'] = module_output

            return throw_json_success("Advanced System Status", output)

        @app.route('/engine/rebootInfo', methods=['GET'])
        def get_reboot_info():
            data = self.getRebootInfo()

            response = throw_json_success("Reboot information", data)
            return response

        @app.route('/<path:module>/status', methods=['GET'])
        def get_module_status(module):
            m = self.modulesTable[module]

            return throw_json_success("Status of " + str(m.moduleName), m.status)

        @app.route('/<path:module>/online', methods=['GET'])
        def online_module(module):
            m = self.modulesTable[module]
            m.online()

            return throw_json_success("Turning online " + str(module), module)

        @app.route('/<path:module>/offline', methods=['GET'])
        def offline_module(module):
            m = self.modulesTable[module]
            m.offline()

            return throw_json_success("Turning offline " + str(module), module)

        @app.route('/<path:module>/reboot', methods=['POST'])
        def reboot_module(module):
            json_input = request.data
            json_data = json.loads(json_input.decode('utf-8'))

            rebootSeconds = json_data['rebootTime']

            # Creating a new reboot event
            rebootTime = datetime.datetime.now() + datetime.timedelta(seconds = rebootSeconds)
            def rebootCompleteFunction(e):
                e.data['module'].rebootStatus = False

                # Now we attempt to 'online' the module!
                e.data['module'].attemptOnline()

            extraData = {}
            extraData['module'] = self.modulesTable[module]

            e = Event(rebootTime, rebootCompleteFunction, "time", extraData, module)
            self.eventSystem.add(e)

            # Enabling the reboot
            self.modulesTable[module].rebootStatus = True

            # Adding a reboot initiated to the logging
            self.modulesTable[module].log.appendLog("Rebooting", 0)

            # Turning offline the module for now
            self.modulesTable[module].offline()

            return throw_json_success("Rebooting " + str(module), self.getRebootInfo())


        @app.route('/engine/time', methods=['GET'])
        def get_engine_time():
            output = self.getTime()
            return throw_json_success("Current Time", output)

        @app.route('/engine/resource/ban', methods=['POST'])
        def ban_resource_from_pool():
            json_input = request.data
            json_data = json.loads(json_input.decode('utf-8'))

            resource = json_data['resource']
            module = json_data['module']

            self.resourcePool.addToBanList(module, resource)

            return throw_json_success("Banned module", True)

        @app.route('/engine/resource/unban', methods=['POST'])
        def unban_resource_from_pool():
            json_input = request.data
            json_data = json.loads(json_input.decode('utf-8'))

            resource = json_data['resource']
            module = json_data['module']

            self.resourcePool.removeFromBanList(module, resource)

            return throw_json_success("Banned module", True)

    # Getting the system information
    def getSystemsStatus(self):
        data = {}
        data['engineStatus'] = self.status
        moduleStatus = {}
        for m in self.modules:
            moduleStatus[m.moduleName] = m.status
        data['moduleStatus'] = moduleStatus

        return data

    # Supporting engine functions
    def getTime(self):
        """
        time = datetime.datetime.now()
        minustime = time - self.startTime
        hours, minutes, seconds, micro = minustime.seconds // 3600, minustime.seconds // 60, minustime.seconds, minustime.microseconds
        minutes, seconds, micro = minutes % 60, seconds % 60, micro % 1000
        
        if hours <= 9:
            hours = '0' + str(hours)
        if minutes <= 9:
            minutes = '0' + str(minutes)
        if seconds <= 9:
            seconds = '0' + str(seconds)
        output = str(hours) + ":" + str(minutes) + ":" + str(seconds)
        """ 
        date_handler = lambda obj: (
            obj.isoformat()
            if isinstance(obj, (datetime.datetime, datetime.date))
            else None
        )
        return json.dumps(self.startTime, default=date_handler)

    def getRebootInfo(self):
        # Getting our reboot info
        data = {}
        for m in self.modules:
            moduleData = {}
            moduleData['rebootTime'] = m.rebootTime
            moduleData['rebootStatus'] = m.rebootStatus
            data[m.moduleName] = moduleData

        return data

    def get_system_logs(self):
        output = {}
        for key in self.modulesTable:
            module = self.modulesTable[key]
            output[key] = module.get_logs()
        return output

    def getResourceLevels(self):
        data = self.resourcePool.getFullOutput()
        return data

    def generateSystemHash(self):
        return ""

    def getMeetingData(self):
        date_handler = lambda obj: (
            obj.isoformat()
            if isinstance(obj, (datetime.datetime, datetime.date))
            else None
        )

        data = {}
        data['isMeeting'] = self.meetingMode
        data['meetingTime'] = json.dumps(self.meetingStartTime, default=date_handler)
        data['meetingMS'] = self.totalMeetingAdjustTimeMS

        return data

    def validateOverride(self, command):
        if command[0] == '9':
            return 'Destroyed'
        elif command[0] == 'A':
            return 'Repaired'
        else:
            return 'False'

class EngineRunner:

    def __init__(self, engine, processSpeed):
        self.engine = engine
        self.processSpeed = processSpeed

    def run(self):
        while True:
            # Skipping if in meeting mode
            if self.engine.meetingMode:
                time.sleep(self.processSpeed)
                continue

            # Processing events
            self.processAllEvents()

            # Processing resources
            self.processResourceRequests()

            # Extra processing
            self.processModulesExtra()

            # Running
            time.sleep(self.processSpeed)

    def processResourceRequests(self):
        for module_name in self.engine.modulesTable:
            module = self.engine.modulesTable[module_name]
            module.processResourceAddToPool()

        for module_name in self.engine.modulesTable:
            module = self.engine.modulesTable[module_name]
            module.processResourceRemoveFromPool()
        
    def processAllEvents(self):
        # Attempting to process time-based events
        eq = self.engine.eventSystem

        for event in eq.eventList:
            # Checking if the time is past the current time, which is the trigger
            if event.canTrigger():
                print("Processing " + str(event))
                event.trigger()

        # Pruning triggered events
        eq.prune()

    def processModulesExtra(self):
        for module_name in self.engine.modulesTable:
            module = self.engine.modulesTable[module_name]
            module.processExtra()

# Credentials application that does credential stuff
class CredentialsApp(Module):

    def __init__(self, engine, resourcePool):
        # Onlining credential servers
        super().__init__("cred", engine, resourcePool) 

        # Table of the username and password
        self.credTable = {}
        self.credTable['admin'] = 'admin'
        
        self.nametable = {}
        self.nametable['admin'] = 'Administrator'

    def loadApp(self, app):

        @app.route('/' + str(self.moduleName) + '/status', methods=['GET'])
        def get_module_status_cred():
            # Getting our engine status
            response = throw_json_success("Status", self.status)

            return response

        @app.route('/cred/hack', methods=['POST'])
        def attempt_hack():
            json_input = request.data
            json_data = json.loads(json_input.decode('utf-8'))

            username = json_data['username']
            module = json_data['module']
            
            # Getting display account
            display_username = "???UNKNOWN???"
            if username in self.nametable:
                display_username = self.nametable[username]

            if username not in self.credTable:
                log = "Failed hack for username of " + str(display_username) + " on module " + str(module)
                self.log.appendLog(log, 2)

                # Also appending it to the modules logs, if the module exists
                moduleObj = self.engine.modulesTable[module]
                moduleObj.log.appendLog(log, 2)
                return throw_json_error(400, "Invalid credential")

            else:
                log = "Hack for username of " + str(display_username) + " on module " + str(module)
                self.log.appendLog(log, 2)

                # Also appending it to the modules logs, if the module exists
                moduleObj = self.engine.modulesTable[module]
                moduleObj.log.appendLog(log, 2)

                return throw_json_success("Hack", display_username)

            

        @app.route('/cred/validate', methods=['POST'])
        def attempt_login():
            json_input = request.data
            json_data = json.loads(json_input.decode('utf-8'))

            username = json_data['username']
            password = json_data['password']
            module = json_data['module']

            # Getting display account
            display_username = "???UNKNOWN???"
            if username in self.nametable:
                display_username = self.nametable[username]

            # Validate default admin
            output = False
            if username in self.credTable and self.credTable[username] == password:
                output = True

            if (output):
                log = "Valid credentials for user " + str(display_username) + " on module " + str(module)
                self.log.appendLog(log)

                # Also appending it to the modules logs, if the module exists
                moduleObj = self.engine.modulesTable[module]
                moduleObj.log.appendLog(log)
            else:
                log = "Invalid credentials for user " + str(display_username) + " on module " + str(module)
                self.log.appendLog(log, 1)

                # Also appending it to the modules logs, if the module exists
                moduleObj = self.engine.modulesTable[module]
                moduleObj.log.appendLog(log, 1)


            data = {}
            data['valid'] = output
            data['username'] = display_username
            response = throw_json_success("Validation status", data)

            return response

        @app.route('/cred/add', methods=['POST'])
        def add_cred():
            json_input = request.data
            json_data = json.loads(json_input.decode('utf-8'))

            username = json_data['username']
            password = json_data['password']
            fullname = json_data['name']

            self.credTable[username] = password
            self.nametable[username] = fullname

            output = {}
            output['credentials'] = self.credTable
            output['names'] = self.nametable

            return throw_json_success("Success", output)

        @app.route('/cred/delete', methods=['POST'])
        def delete_cred():
            json_input = request.data
            json_data = json.loads(json_input.decode('utf-8'))

            username = json_data['username']
            self.credTable.pop(username, None)
            self.credTable.pop(username)

            return throw_json_success("Success", True)


        @app.route('/cred/get', methods=['GET'])
        def get_cred():
            # Getting all credentials
            output = {}
            output['credentials'] = self.credTable
            output['names'] = self.nametable

            response = throw_json_success("Credentials", output)

            return response

# Wrapper administration portal class
class AdminModule(Module):

    def __init__(self, engine, resourcePool):
        super().__init__("admin", engine, resourcePool) 

    def loadApp(self, app):
        print("Not yet implemented")