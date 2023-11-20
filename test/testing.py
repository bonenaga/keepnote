import sys
import os
import shutil
import unittest
import argparse
import importlib


class OptionParser(argparse.ArgumentParser):
    def __init__(self, *args):
        argparse.ArgumentParser.__init__(self, *args)

    def exit(self, code, text):
        pass


def clean_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path)


def makedirs(path):
    if not os.path.exists(path):
        os.makedirs(path)


def make_clean_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)


def list_tests(stack=0):
    # get environment
    var = importlib.import_module("__main__").__dict__

    for name, obj in var.items():
        if isinstance(obj, type) and issubclass(obj, unittest.TestCase):
            for attr in dir(obj):
                if attr.startswith("test"):
                    print("%s.%s" % (name, attr), end=" ")
                    doc = getattr(obj, attr).__doc__
                    if doc:
                        print("--", doc.split("\n")[0])
                    else:
                        print()


def test_main():
    o = OptionParser()
    o.add_argument("-l", "--list_tests", action="store_true")

    conf, args = o.parse_known_args()

    if conf.list_tests:
        list_tests(1)
        return

    unittest.main()


if __name__ == "__main__":
    test_main()
