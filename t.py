# import logging
#
# logging.basicConfig(level=logging.DEBUG,
#                           format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
#                           datefmt='%a, %d %b %Y %H:%M:%S', filename='crawler.log', filemode='w')
# logging.info('aaa')
# from article import *
# connect('test')
# article = Article(link='www', title='aaa', summary='bbb')
# article.content = 'ccc'
# article.save()
# import datetime
# import sys
#
#
# class QqWorker(object):
#     def __init__(self, start=datetime.date(2009, 1, 1), end=datetime.date(2009, 1, 2)):
#         self.beginDate = start
#         self.endDate = end
#
#     def start(self):
#         print(self.beginDate)
#         print(self.endDate)
#
#
# if __name__ == '__main__':
#     qqWorker = {}
#     if len(sys.argv) > 2:
#         start_str = sys.argv[1]
#         end_str = sys.argv[2]
#         try:
#             start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
#             end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
#             qqWorker = QqWorker(start_date, end_date)
#         except StandardError:
#             print('incorrect argument ,enter like : start 2015-01-01 2015-01-10')
#             exit(0)
#     else:
#         qqWorker = QqWorker()
#     qqWorker.start()

