from __future__ import print_function

def very_inefficient(recursion, accumulator):
    if recursion > 0:
        accumulator = accumulator + ('f' * 1024 + '\n')
        very_inefficient(recursion - 1, accumulator)
    else:
        some_str = ' ' * (10 ** 9 / 4)
        return accumulator


def example_handler(event, context):
    result = very_inefficient(512, '')
    return event['key1']#echo first key value