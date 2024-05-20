#!/usr/bin/env python

from math import e
import sys

from git_ai.cmd import diff
from git_ai.cmd import log
from git_ai.cmd import merge_exp
from git_ai.cmd import input_repo
from git_ai.cmd import init
from git_ai.cmd import format_error


def main():
    try:
        if len(sys.argv) < 2:
            print('Usage: git-ai <command> [<args>]')
            sys.exit(1)

        if sys.argv[1] == 'init':
            init()
        elif sys.argv[1] == 'diff':
            diff(sys.argv)
        elif sys.argv[1] == 'log':
            log(sys.argv)
        elif sys.argv[1] == 'merge-exp':
            merge_exp(sys.argv)
        elif sys.argv[1] == 'input-repo':
            input_repo(sys.argv)
        else:
            print('git-ai 0.1.0')
            print('Usage: git-ai <command> [<args>]')
    except Exception as e:
        print(format_error(e))
        sys.exit(1)
