__author__ = 'dominiczippilli'
import traceback
import sys

def import_fail(err):
    print(
        "\nOops! Ensure the module has a function named 'lambda_handler' with a signature like: def lambda_handler (event, context)\n")
    print(err.message)
    sys.exit(1)


def event_fail(err, filename):
    print("There was a problem parsing your JSON event file, %s:" % filename)
    print(err.message + '\n')
    sys.exit(1)


def invoke_fail():
    print(
        "\nThere was an error running your function.\n")
    traceback.print_exc()
    sys.exit(1)