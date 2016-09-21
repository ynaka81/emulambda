from __future__ import print_function
import argparse
import gc
from importlib import import_module
import json
import os
import resource
import sys
import time
import traceback
import boto3

from emulambda.timeout import timeout, TimeoutError
from emulambda.render import render_result, render_summary

__author__ = 'dominiczippilli'
__description__ = 'A local emulator for AWS Lambda for Python.'


def main():
    sys.path.append(os.getcwd())
    sys.path.append("./lib")
    args = parseargs()

    # Get process peak RSS memory before execution
    pre_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    # Import the lambda
    lfunc = import_lambda(args.lambdapath)

    # Build statistics dictionary
    stats = {'clock': list(), 'rss': list()}

    def execute(_event=None, _context=None):
        """
        Encapsulation of _event-running code, with access to collectors and other variables in main() scope. Used
        for both single-run and stream modes.
        :param _event: A valid Lambda _event object.
        :return: Void.
        """
        # Invoke the lambda
        # TODO consider refactoring to pass stats through function
        result, exec_clock = invoke_lambda(lfunc, _event, _context, args.timeout, args.role)

        # Get process peak RSS memory after execution
        exec_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - pre_rss

        # Store statistics
        stats['clock'].append(exec_clock)
        stats['rss'].append(exec_rss)

        # Render the result
        render_result(args.verbose, args.lambdapath, result, exec_clock, exec_rss)

    if args.stream:
        # Enter stream mode
        emit_to_function(args.verbose, args.eventfile, execute)
        render_summary(stats) if args.verbose else None
    elif args.contextfile:
        context = read_file_to_object(args.contextfile)
        event = read_file_to_string(args.eventfile)
        execute(parse_event(event), context)
    else:
        # Single event mode
        event = read_file_to_string(args.eventfile)
        execute(parse_event(event))


def parseargs():
    """
    Parse command line arguments.
    :return: Argument namespace (access members with dot).
    """
    parser = argparse.ArgumentParser(
        description='Python AWS Lambda Emulator. At present, AWS Lambda supports Python 2.7 only.')
    parser.add_argument('lambdapath',
                        help='An import path to your function, as you would give it to AWS: `module.function`.')
    parser.add_argument('eventfile', help='A JSON file to give as the `event` argument to the function.')
    parser.add_argument('contextfile', help='A JSON file to give as the `context` argument to the function.',
                        nargs='?')
    # TODO -- investigate if stream can be auto-detected
    parser.add_argument('-s', '--stream', help='Treat `eventfile` as a Line-Delimited JSON stream.',
                        action='store_true')
    parser.add_argument('-r', '--role', help='ARN of the role to execute your Lambda function (your user must have AssumeRole priviledge and your user ARN must be in Lambda\'s execution role TrustedPolicy).',
                        type=str)
    parser.add_argument('-t', '--timeout', help='Execution timeout in seconds. Default is 300, the AWS maximum.',
                        type=int,
                        default=300)
    parser.add_argument('-v', '--verbose', help='Verbose mode. Provides exact function run, timing, etc.',
                        action='store_true')
    return parser.parse_args()


def import_lambda(path):
    """
    Import a function from a given module path and return a reference to it.
    :param path: Path to function, given as [module 1].[module 2...n].[function]
    :return: Python function
    """
    try:
        # Parse path into module and function name.
        path = str(path)
        if '/' in path or '\\' in path:
            raise ValueError()
        spath = path.split('.')
        module = '.'.join(spath[:-1])
        function = spath[-1]
        # Import the module and get the function.
        import_module(module)
        return getattr(sys.modules[module], function)
    except (AttributeError, TypeError) as e:
        print("\nOops! There was a problem finding your function.\n")
        raise e
    except ValueError:
        print("It looks like you've given a Python *file* path as the lambdapath argument. This must be "
              "an *import* path, following the form of [module 1].[module 2...n].[function]" + '\n' +
              "Perhaps it is something like `" + '.'.join(path.split('/')[-1:]) + "`?")
        sys.exit(1)

def read_file_to_object(filename):
    """
    Deserialize JSON into Python Object to be compliant with Lambda Context Object.
    More info: http://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html
    :param filename: A valid path to a file
    :return: Object.
    """

    class JSON2Object(object):
        def __init__(self, jsonfile):
            self.__dict__ = parse_event(jsonfile)

    jsonfile = read_file_to_string(filename)
    return JSON2Object(jsonfile)


def read_file_to_string(filename):
    """
    Reads from a file or stdin, loading the data into a string and returning the string.
    :param filename: A valid path to a file, or '-' for stdin.
    :return: String.
    """
    try:
        with sys.stdin if filename is '-' else open(filename, 'r') as event_file:
            return event_file.read()
    except IOError as e:
        e.message = "File not found / readable!"
        print("There was a problem parsing your JSON event.")
        print(e.message)
        raise e


def parse_event(eventstring):
    """
    Provides parsing of event strings into objects. In its own function for error-handling, clarity.
    :param eventstring: A JSON string representing an event.
    :return: An Event object (which is an arbitrary dictionary).
    """
    try:
        return json.loads(eventstring)
    except ValueError as e:
        print("There was a problem parsing your JSON event.")
        print(e.message)
        raise e

def create_boto3_default_session(roleARN):
    """
    Invoke STS to Assume the given role and create a default boto3 session
    :param roleARN: The IAM rolename to assume.  TrustedPolicy must include the following principals
                    ["lambda.amazonaws.com", "arn:aws:iam:<YOUR ACCOUNT ID>::user/<YOUR USER>"]
    """
    print("Going to assume role %s" % roleARN)
    stsClient = boto3.client("sts")
    creds = stsClient.assume_role(RoleArn=roleARN,RoleSessionName='emulambda',)
    print("Setting up the default session")
    boto3.setup_default_session(aws_access_key_id=creds['Credentials']['AccessKeyId'],
                                aws_secret_access_key=creds['Credentials']['SecretAccessKey'],
                                aws_session_token=creds['Credentials']['SessionToken'])


def invoke_lambda(lfunc, event, context, t, roleARN):
    """
    Invoke an AWS Lambda-compatible function.
    :param lfunc: The lambda compatible function (def f(event, context))
    :param event: An event object (really, an arbitrary dictionary)
    :param context: A context object
    :param t: Timeout. If this function does not complete in this time, execution will fail.
    :param roleRN: the ARN to Lambda's function execution role.  Your IAM user must be in the role's TrustedPolicy
    :return: Function result (type dependent on function implementation), execution time as int.
    """

    @timeout(t)
    def _invoke_lambda(l, e, c):
        # TODO investigate suitability of timeit here
        s = time.time()
        r = l(e, c)
        x = (time.time() - s) * 1000  # convert to ms
        return r, x

    try:
        if roleARN:
            create_boto3_default_session(roleARN)

        return _invoke_lambda(lfunc, event, context)
    except TimeoutError:
        print("Your lambda timed out! (Timeout was %is)\n" % t)
        return "EMULAMBDA: TIMEOUT ERROR", -1
    except BaseException:
        # While this is normally a too-broad exception, since we cannot know the lambda's errors ahead of time, this is appropriate here.
        print(
            "\nThere was an error running your function. Ensure it has a signature like `def lambda_handler (event, context)`.\n")
        traceback.print_exc()
        return "EMULAMBDA: LAMBDA ERROR", -1


def emit_to_function(verbose, stream, func):
    """
    Emit lines from a stream to a function. Each line must contain a JSON string, and the function must take the resulting object.
    :param stream: A file-like object providing a LDJSON stream.
    :param func: A function to invoke with objects from the stream.
    :return: Void.
    """
    print("Entering stream mode.") if verbose else None
    i = 1
    try:
        with sys.stdin if stream is '-' else open(stream, 'r') as event_stream:
            for line in event_stream:
                gc.collect()  # force GC between each run to get quality memory usage sample
                print(
                    "\nObject %i %s" % (i, line.rstrip()[:65] + ('...' if len(line) > 65 else ''))) if verbose else None
                i += 1
                func(json.loads(line), None)
    except ValueError as e:
        print("There was a problem parsing your JSON event.")
        print(e.message)
        raise e
    except IOError as e:
        print("There was a problem parsing your JSON event.")
        print(e.message)
        raise e
