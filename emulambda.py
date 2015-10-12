#!/usr/bin/env python
from __future__ import print_function
import argparse
import gc
from importlib import import_module
import json
import math
import numpy
import resource
import sys
import time
import traceback

from hurry.filesize import size

from timeout import timeout, TimeoutError

__author__ = 'dominiczippilli'
__description__ = 'A local emulator for AWS Lambda for Python.'


def main():
    args = parseargs()

    # Get process peak RSS memory before execution
    pre_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    # Import the lambda
    lfunc = import_lambda(args.lambdapath)

    # Build statistics dictionary
    stats = {'clock': list(), 'rss': list()}

    def execute(_event):
        """
        Encapsulation of _event-running code, with access to collectors and other variables in main() scope. Used
        for both single-run and stream modes.
        :param _event: A valid Lambda _event object.
        :return: Void.
        """
        # Invoke the lambda
        result, exec_clock = invoke_lambda(lfunc, _event, None, args.timeout)  # TODO consider refactoring to pass stats through function

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
    parser.add_argument('-s', '--stream', help='Treat `eventfile` as a Line-Delimited JSON stream.',
                        action='store_true')  # TODO -- investigate if this can be auto-detected
    parser.add_argument('--timeout', help='Execution timeout in seconds. Default is 300, the AWS maximum.', type=int,
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
        spath = path.split('.')
        module = '.'.join(spath[:-1])
        function = spath[-1]
        # Import the module and get the function.
        import_module(module)
        return getattr(sys.modules[module], function)
    except (AttributeError, TypeError) as e:
        print("\nOops! There was a problem finding your function.\n")
        print(e.message)
        raise e


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


def invoke_lambda(lfunc, event, context, t):
    """
    Invoke an AWS Lambda-compatible function.
    :param lfunc: The lambda compatible function (def f(event, context))
    :param event: An event object (really, an arbitrary dictionary)
    :param context: A context object
    :param t: Timeout. If this function does not complete in this time, execution will fail.
    :return: Function result (type dependent on function implementation), execution time as int.
    """
    @timeout(t)
    def _invoke_lambda(l, e, c):
        s = time.time()  # TODO investigate suitability of timeit here
        r = l(e, c)
        x = (time.time() - s) * 1000  # convert to ms
        return r, x

    try:
        return _invoke_lambda(lfunc, event, context)
    except TimeoutError:
        print("Your lambda timed out! (Timeout was %is)\n" % t)
        return None  # TODO this used to be sys.exit(1). Revise this mechanic now that there is a batch mode.
    except BaseException:
        # While this is normally a too-broad exception, since we cannot know the lambda's errors ahead of time, this is appropriate here.
        print("\nThere was an error running your function. Ensure it has a signature like `def lambda_handler (event, context)`.\n")
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
                print("\nObject %i %s" % (i, line.rstrip()[:65] + ('...' if len(line) > 65 else ''))) if verbose else None
                i += 1
                func(json.loads(line))
    except ValueError as e:
        print("There was a problem parsing your JSON event.")
        print(e.message)
        raise e
    except IOError as e:
        print("There was a problem parsing your JSON event.")
        print(e.message)
        raise e


def render_result(verbose, lambdapath, result, exec_clock, exec_rss):
    """
    Render the result of a lambda execution, with profiling info if verbose.
    :param lambdapath: Path given for the lambda.
    :param result: Result of the execution.
    :param exec_clock: Execution clock time.
    :param exec_rss: Execution RSS.
    :return: Void.
    """
    if verbose:
        print("Executed %s" % lambdapath)
        print("Estimated...")
        print("...execution clock time:\t\t %ims (%ims bucket)" % (
            exec_clock,
            int(math.ceil(exec_clock / 100.0)) * 100
        ))
        print("...execution peak RSS memory:\t\t %s (%i bytes)" % (size(exec_rss), exec_rss))
        print("----------------------RESULT----------------------")
    print(str(result))


def render_summary(stats):
    """
    Render summary of an event stream run.
    :param stats: Dictionary('clock':list()<float>, 'rss':list()<int>)
    :return: Void.
    """
    print('\nSummary profile from stream execution:')
    print('Samples: %i' % len(stats['clock']))
    if -1 in stats['clock']:
        print('(ERRORS DETECTED: Removing timing samples from aborted invocations.)')
        stats['clock'] = [x for x in stats['clock'] if x > 0]
    print('Clock time:\n'
          '\tMin: %ims, Max: %ims, Median: %ims, Rounded Standard Deviation: %sms' % (
              min(stats['clock']),
              max(stats['clock']),
              sorted(stats['clock'])[math.trunc(len(stats['clock']) / 2)],
              math.trunc(math.ceil(numpy.std(stats['clock'], ddof=1)))
          ))
    print('Peak resident set size (memory):\n'
          '\tMin: %s, Max: %s' % (
              size(min(stats['rss'])),
              size(max(stats['rss']))
          ))


if __name__ == '__main__':
    main()
