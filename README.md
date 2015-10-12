# emulambda
Copyright Fugue, Inc. 2015

## Recommended Uses
Use `emulambda` to emulate the AWS Lambda API locally. The utility will help you to
debug and profile your lambda functions. This shortens your feedback loop and
reduces development cost and time.

## Features
Present:
  - Run an AWS-compatible lambda function
  - Take event from file
  - Set timeout up to 300s
  - Send lambda result to stdout
  - Estimate time and memory usage in verbose mode

Planned:
  - Take event via stdin
  - Support deployment package format
  - SQS
  - Kinesis
  - AWS Event lib
  - Contexts?

## Usage

`emulambda.py [-h] [--timeout TIMEOUT] [-v] lambdamod eventfile`

### Positional Arguments:
  - `lambdamod`
    - A Python 2.7 module name (not file name!) containing your Lambda function.
  - `eventfile`
    - A JSON file to give as the `event` argument to the function.

### Optional Arguments:
  - `-h, --help`
    - Show a help message and exit.
  - `--timeout TIMEOUT`
    - Execution timeout in seconds. Default is 300, the AWS maximum.
  - `-v, --verbose`
    - Verbose mode. Provides exact function run, timing, etc.

## Quick Start Example

From the repository root, run:
`./emulambda.py example example/example.json -v`

You should see output similar to the following:
```
Executed lambda_handler in module example
Estimated...
...execution clock time:		 0.192309 seconds
...execution user mode time:	 0.074047 seconds
...execution peak RSS memory:	 368M (386195456 bytes)
----------------------RESULT----------------------
value1
```

#### What's happening?

In this example, `emulambda` is:
  1. Loading the `lambda_handler` function from the `example` module
  1. Deserializing `example/example.json` as the `event` argument for the function.
  1. Invoking the function, timing and measuring memory consumption.
  1. Reporting on resource usage.
  1. Printing the function result.
