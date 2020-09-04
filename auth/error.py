# This is a way that we are able to handle errors
# Its just a genericized way of handling errors to be quite honest with you
import json

def throw_json_error(code, description):
    error = {
        "code": code,
        "reason": description
    }

    return error


def throw_json_success(description, data):

    success = {
        "code": 200,
        "reason": description,
        "data": data
    }

    return success
