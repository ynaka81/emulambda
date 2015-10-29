# emulambda
Copyright Fugue, Inc. 2015

**EMULA**tes AWS La**MBDA**

## Recommended Uses
Use `emulambda` to emulate the AWS Lambda API locally. It provides a Python "harness" that you can use to wrap your
function and run/analyze it.

  - Development
    - Run your lambda functions instantly locally, without packaging and sending to AWS.
    - Shorten your feedback loop on lambda executions.
    - Easily attach debuggers to your lambda.
    - Run your lambda locally.
  - Testing
    - Easily integrate with test tools using a simple CLI and various input methods.
    - Use stream mode to test many cases or run fuzz tests.
    - Use profiling information to identify expensive/problematic lambdas early.


## Features
Present:
  - Run an AWS-compatible lambda function
  - Take event from file or stdin
    - Also accepts LDJSON stream of events (manually switched)
  - Set timeout up to 300s
  - Send lambda result to stdout
  - Estimate time and memory usage in verbose mode
    - Also produces summary report & statistics when given a stream.


Planned:
  - SQS (although directing AWS CLI to stdin might be easier)
  - Kinesis
  - AWS event library, for common integrations
  - Context support

## Installation
1. `git clone` [the Emulambda repo] (https://github.com/fugue/emulambda/)
2. Install it with `pip install -e emulambda` (You might need to sudo this command if you're using your system Python instead of a virtualenv or similar.)


## Usage

```
usage: emulambda.py [-h] [-s] [-t TIMEOUT] [-v] lambdapath eventfile

Python AWS Lambda Emulator. At present, AWS Lambda supports Python 2.7 only.

positional arguments:
  lambdapath            An import path to your function, as you would give it
                        to AWS: `module.function`.
  eventfile             A JSON file to give as the `event` argument to the
                        function.

optional arguments:
  -h, --help            show this help message and exit
  -s, --stream          Treat `eventfile` as a Line-Delimited JSON stream.
  -t TIMEOUT, --timeout TIMEOUT
                        Execution timeout in seconds. Default is 300, the AWS
                        maximum.
  -v, --verbose         Verbose mode. Provides exact function run, timing,
                        etc.
```

## Quick Start

### Single-Event Mode

From the repository root, run:
`./emulambda.py example.example_handler - -v < example/example.json`

You should see output similar to the following:
```
Executed example.example_handler
Estimated...
...execution clock time:		 0.192309 seconds
...execution peak RSS memory:	 368M (386195456 bytes)
----------------------RESULT----------------------
value1
```

Note that without the `-v` switch, the function return is printed to `stdout`
with no modification or other information.

```
$ ./emulambda.py example.example_handler example/example.json
value1
```

#### What's happening?

In this example, `emulambda` is:
  1. Loading the `example_handler` function from the `example` module.
  1. Deserializing `stdin` (which is the contents of `example/example.json`) as the `event` argument for the function.
  1. Invoking the function, timing, and measuring memory consumption.
  1. Reporting on resource usage.
  1. Printing the function result.

### Event Stream Mode

From the repository root, run:
`./emulambda.py example.example_handler - -s -v -t 2 < example/ex-stream.ldjson`

You should see output similar to the following:
```
Entering stream mode.

Object 1 { "key1": "value1", "key2": "value2", "key3": "value3" }
Executed example.example_handler
Estimated...
...execution clock time:		 196ms
...execution peak RSS memory:		 368M (385933312 bytes)
----------------------RESULT----------------------
value1

Object 2 { "key2": "value2b", "key3": "value3b" }

There was an error running your function. Ensure it has a signature like `def lambda_handler (event, context)`.

Traceback (most recent call last):
.
.
[...snip...]
.
.
Object 18 { "key1": "value1b", "key2": "value2b", "key3": "value3b" }
Executed example.example_handler
Estimated...
...execution clock time:		 190ms
...execution peak RSS memory:		 396M (416256000 bytes)
----------------------RESULT----------------------
value1b

Summary profile from stream execution:
Samples: 18
(ERRORS DETECTED: Removing timing samples from aborted invocations.)
New sample size: 17
Clock time:
	Min: 184ms, Max: 198ms, Median: 189ms, Rounded Standard Deviation: 5ms
Peak resident set size (memory):
	Min: 367M, Max: 396M
```

#### What's happening?

In this example, `emulambda` is:
  1. Loading the `example_handler` function from the `example` module.
  1. Streaming Line-Delimited JSON (LDJSON) lines from `stdin` (which is the
  contents of `example/ex-stream.ldjson`) as `event` arguments.
  1. Once per `event` object, invoking the function, reporting on resource usage, and printing the function
  result.
  1. At 'event' number 2, there is an intentional error. Note that `emulambda`
  reports the error and recovers.
  1. After running each event through the lambda, reporting aggregate timing and
  memory information.

## How Profiling Works

The profiling in `emulambda` is meant to help with billing estimation more than
anything else. Since we can only guess at some AWS Lambda internals, we've run
some experiments against the service to partially reverse-engineer the metrics it
uses for billing. Therefore:
  * Clock time is as close as possible to function execution. It does not include
  time spent loading the module(s), though that is a penalty you would pay the
  first time you execute the lambda in AWS.
  * System-reported peak RSS (resident set size) is used for memory estimation.
  This represents real memory use, not the use of virtual memory.

The authors of this project make no guarantees whatsoever that the profiling
information given by `emulambda` is accurate. It may not correlate with what AWS bills.
Many variables, including the resources allocated to the function runtime by AWS,
may have an impact on the real billed amount.
