from distutils.core import setup


setup(
    name='emulambda',
    version='0.1',
    packages=['emulambda'],
    scripts=['bin/emulambda'],
    url='http://www.fugue.co',
    license='Apache 2.0',
    author='dominiczippilli',
    author_email='dom@fugue.co',
    description='Python emulator for AWS Lambda.',
    install_requires=[
        'hurry.filesize',
        'numpy',
        'boto3',
        'nose',
        'psutil' #not strictly required by linux, but I couldn't figure out how to have per-platform builds easily
      ],


)
