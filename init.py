    
##########################
### Base level imports ###
##########################

from flask import Flask
from flask_cors import CORS
import json
import threading
import time
import os
from auth.error import *

########################
# Setting up the flask #
########################

app = Flask('SpaceYBackEnd')
CORS(app)

###########################
# Setting up load imports #
###########################
@app.route('/')
def init_route():
    response = json.dumps(throw_json_error(404, "Page not found"))
    print("Returning " + response)
    return response

### Initializing our engine
from main.engine import Engine
from main.engine import EngineRunner
e = Engine(app)
runner = EngineRunner(e, 1)

# Mutlithread start
#x = threading.Thread(target=runner.run, args=())
#x.start()

app.run(host='0.0.0.0')

    