# -*- encoding: utf-8 -*
import sys
import datetime
from qq import *
from ifeng import *
from sohu import *

if __name__ == '__main__':
    qqWorker = {}
    fengWorker = {}
    if len(sys.argv) > 1:
        type = sys.argv[1]
    else:
        type = ''
    if len(sys.argv) > 3:
        start_str = sys.argv[2]
        end_str = sys.argv[3]
        try:
            start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
            qqWorker = QqWorker(start_date, end_date)
            sohuWorker = SohuWorker(start_date, end_date)
            fengWorker = FengWorker(start_date, end_date)
        except StandardError:
            print('incorrect argument ,enter like : start qq 2015-01-01 2015-01-10')
            exit(0)
    else:
        qqWorker = QqWorker()
        sohuWorker = SohuWorker()
        fengWorker = FengWorker()
    if type == 'qq':
        connect('qq')
        qqWorker.start()
    elif type == 'sohu':
        connect('sohu')
        sohuWorker.start()
    elif type == 'ifeng':
        connect('ifeng')
        fengWorker.start()
        # else:
        #     connect('qq')
        #     qqWorker.start()
        #     connect('sohu')
        #     sohuWorker.start()
        #     connect('ifeng')
        #     fengWorker.start()
