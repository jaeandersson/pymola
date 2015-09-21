#!/usr/bin/env python
"""
FSM compiler.
"""
from __future__ import print_function
import sys
import antlr4
from generated.FSMLexer import FSMLexer
from generated.FSMParser import FSMParser
from generated.FSMListener import FSMListener
import argparse

class KeyPrinter(FSMListener):
    "Simple example"
    def exitFsm_state(self, ctx):
        "print msg when leaving state"
        print("leaving state")

def main(argv):
    "The main function"
    parser = argparse.ArgumentParser()
    parser.add_argument('filename')
    args = parser.parse_args()
    text = antlr4.FileStream(args.filename)
    lexer = FSMLexer(text)
    stream = antlr4.CommonTokenStream(lexer)
    parser = FSMParser(stream)
    tree = parser.fsm_main()
    print(tree.toStringTree(recog=parser))
    printer = KeyPrinter()
    walker = antlr4.ParseTreeWalker()
    walker.walk(printer, tree)

if __name__ == '__main__':
    main(sys.argv)

# vim: set et ft=python fenc=utf-8 ff=unix sts=0 sw=4 ts=4 :
