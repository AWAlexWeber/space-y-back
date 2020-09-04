# Event queue system
import datetime
class EventSystem:

    def __init__(self):
        self.eventList = list()

    def add(self, e):
        self.eventList.append(e)

    # Prunes out already triggered events
    def prune(self):
        newEventList = list()

        for event in self.eventList:
            if not event.didTrigger:
                newEventList.append(event)

        self.eventList = newEventList

class Event:

    def __init__(self, triggerTime, callback, triggerType, data, name):
        self.triggerTime = triggerTime
        print(callback)
        self.callback = callback
        self.triggerType = triggerType
        self.didTrigger = False
        self.data = data
        self.name = name

    def canTrigger(self):
        if self.didTrigger:
            return False

        if self.triggerType == 'time':
            # Checking the current time
            if datetime.datetime.now() > self.triggerTime:
                return True
            
            else:
                return False

    def trigger(self):
        self.callback(self)
        self.didTrigger = True