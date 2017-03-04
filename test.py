import unittest
import sys
import emulambda
import emulambda.render
import io
__author__ = 'dominiczippilli'


class EmulambdaMainTest(unittest.TestCase):
    def test_main_single_event(self):
        sys.argv = [sys.argv[0], 'example.example_handler', 'example/example.json']
        try:
            emulambda.main()
            assert True
        except BaseException as e:
            self.fail("Main method failed.\n%s" % e.message)

    def test_main_stream(self):
        sys.argv = [sys.argv[0], 'example.example_handler', 'example/ex-stream.ldjson', '-s']
        try:
            emulambda.main()
            assert True
        except BaseException as e:
            self.fail("Main method failed.\n%s" % e.message)


class EmulambdaParseArgsTest(unittest.TestCase):
    def test_parse_args_empty(self):
        sys.argv = [sys.argv[0]]
        try:
            args = emulambda.parseargs()
            self.fail("Command line interface no longer matches testmodule specification.")
        except SystemExit:
            sys.stderr.write("^ ignore above")
            assert True

    def test_parse_args_normal(self):
        sys.argv = [sys.argv[0], 'foo', 'bar']
        try:
            args = emulambda.parseargs()
            assert args
        except BaseException as e:
            self.fail("Basic argument parsing failed.\n%s" % e.message)


class EmulambdaImportLambdaTest(unittest.TestCase):
    def test_import_lambda_file(self):
        try:
            emulambda.import_lambda('/foo/bar')
            self.fail("Somehow, we imported a file.")
        except:
            assert True

    def test_import_lambda_correct_file(self):
        try:
            func = emulambda.import_lambda('testmodule/foo.bar')
            assert func
        except BaseException as e:
            self.fail("Unable to import module and find function.\n%s" % e.message)

    def test_import_lambda_wrong_file(self):
        try:
            emulambda.import_lambda('testmodule/foo.bar.biz')
            self.fail("Somehow, we imported a file.")
        except:
            assert True

    def test_import_lambda_missing(self):
        try:
            emulambda.import_lambda('testmodule.bar')
            self.fail("Didn't detect invalid function.")
        except:
            assert True

    def test_import_lambda(self):
        try:
            func = emulambda.import_lambda('testmodule.foo')
            assert func
        except BaseException as e:
            self.fail("Unable to import module and find function.\n%s" % e.message)


class EmulambdaReadFileToStringTest(unittest.TestCase):
    def test_load_file(self):
        try:
            emulambda.read_file_to_string(__file__)
            assert True
        except BaseException as e:
            self.fail("We failed to read a file.\n%s" % e.message)

    def test_load_stdin(self):
        try:
            sys.stdin = io.BytesIO(b"testdata")
            result = emulambda.read_file_to_string('-')
            assert result == "testdata"
        except BaseException as e:
            self.fail("We failed to read standard input.\n%s" % e.message)


class EmulambdaParseEventTest(unittest.TestCase):
    def test_parse_event(self):
        try:
            event = emulambda.parse_event("""
            { "iamanevent": true }
            """)
            assert event["iamanevent"]
        except BaseException as e:
            self.fail("Event parsing failed.\n%s" % e.message)


class EmulambdaInvokeLambdaTest(unittest.TestCase):
    #TODO: Timeout test?
    def test_invoke_lambda(self):
        try:
            def test_func(e, c):
                return "foo"
            event = {"foo": "bar"}
            context = {"baz": "qux"}
            emulambda.invoke_lambda(test_func, event, context, 300, None)
            assert True
        except BaseException as e:
            self.fail("Failed to invoke lambda.\n%s" % e.message)


class EmulambdaEmitToFunctionTest(unittest.TestCase):
    def test_emit_to_function(self):
        try:
            sys.stdin = io.BytesIO(b'{"foo":"bar"}\n{"foo":"baz"}')

            def test_func(e, c):
                return e["foo"]

            emulambda.emit_to_function(False, '-', test_func)
        except BaseException as e:
            self.fail("Emit stream to function failed.\n%s" % e.message)


class EmulambdaBillingBucketTest(unittest.TestCase):
    def test_billing_bucket(self):
        try:
            assert emulambda.render.billing_bucket(199) == 200
            assert emulambda.render.billing_bucket(101) == 200
            assert emulambda.render.billing_bucket(99) == 100
        except BaseException as e:
            self.fail("Billing bucket is wrong.\n%s" % e.message)
