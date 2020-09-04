# Log class

class Log:

    def __init__(self, logName):
        self.logName = logName
        self.logData = list()

        self.appendLog("Log initialized", 0)

    def appendLog(self, logMessage, logType=0):
        self.logData.append(LogEntry(logMessage, logType))

    def get_logs(self):
        output = list()
        for logEntry in self.logData:
            output.append((logEntry.logMessage, logEntry.logType))
        return output

class LogEntry:

    def __init__(self, logMessage, logType=0):
        self.logMessage = logMessage
        self.logType = logType