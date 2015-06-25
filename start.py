# -*- encoding: utf-8 -*
import sys
from qq import *
from ifeng import *

if __name__ == '__main__':
    qqWorker = {}
    fengWorker = {}
    if len(sys.argv) > 2:
        start_str = sys.argv[1]
        end_str = sys.argv[2]
        try:
            start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
            qqWorker = QqWorker(start_date, end_date)
        except StandardError:
            print('incorrect argument ,enter like : start 2015-01-01 2015-01-10')
            exit(0)
    else:
        qqWorker = QqWorker()
        fengWorker = FengWorker()
    qqWorker.start()
    # fengWorker.start()
