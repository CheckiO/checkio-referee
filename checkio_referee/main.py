"""
    Testing
    remove this file after all done
"""
import os
import sys
import signal
import logging
import coloredlogs

ROOT = os.path.realpath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, '..'))

from tornado import gen
from tornado.ioloop import IOLoop

from server import RefereeBase

RefereeBase.EXECUTABLE_PATH = '/Users/igorlubimov/sites/code_empyre/mission-template/verification/envs/python_27'


@gen.coroutine
def main():
    def exit_signal(sig, frame):
        logging.info("Trying exit")
        io_loop.add_callback(IOLoop.instance().stop)

    signal.signal(signal.SIGINT, exit_signal)
    signal.signal(signal.SIGTERM, exit_signal)

    coloredlogs.install()
    logging.info('Run...')

    io_loop = IOLoop.instance()
    referee = RefereeBase(io_loop=io_loop)
    referee.start()
    io_loop.start()


if __name__ == "__main__":
    main()
