# -*- encoding: utf-8 -*
import logging
import re

import requests

from pyquery import PyQuery as pq
from worker import *
from article import *
from logger import Logger

logger = Logger(logname='sohu.log', logger=__name__).get_logger()


class SohuWorker(Worker):
    def __init__(self, startdate=date(2015, 1, 1), enddate=date(2015, 1, 2)):
        super(SohuWorker, self).__init__()
        self.beginDate = startdate
        self.endDate = enddate

    # http://news.sohu.com/_scroll_newslist/20090713/news.inc
    # 国内 0 国际 1 社会 2
    __listUrl = 'http://news.sohu.com/_scroll_newslist/{0}/news.inc'
    __referUrl = ''

    def start(self):
        self.get_records()
        day = self.beginDate
        while day <= self.endDate:
            if day not in self.historyDict:
                self.crawl_by_day(day)
            day += Worker.dayDelta
        self.reget_errorlist()

    def get_records(self):
        pass

    def crawl_by_day(self, day):
        date_str = day.strftime("%Y%m%d")
        try:
            r = requests.get(self.__listUrl.format(date_str))
            r.encoding = 'utf-8'
            reg = re.compile(r'\[\d,.*?]')
            if r.status_code == 200:
                items = reg.findall(r.text)
                if len(items) > 0:
                    self.parse_articles_list(items)
                    self.save_by_day(date_str)
        except requests.exceptions.RequestException, e:
            logging.exception(e)
        except StandardError, e:
            logging.error(date_str + ' error')
            logging.exception(e)

    def parse_articles_list(self, articles):
        for i in range(len(articles)):
            # for test
            if i % 50 != 0:
                continue
            # test end
            item = articles[i].strip('[]').split(',')
            if item[0] == '0':
                category = '国内'
            elif item[0] == '1':
                category = '国际'
            elif item[0] == '2':
                category = '社会'
            else:
                continue
            title = item[1].strip(' "')
            link = item[2].strip(' "')
            post_time = item[3].split(' ')[1].rstrip('"')
            item = {'title': title, 'link': link, 'post_time': post_time, 'category': category, 'valid': True}
            self.newsDict[link] = item
            # 重试
            retry = 1
            try:
                self.get_detail(link)
            except StandardError:
                if retry > 0:
                    retry -= 1
                    self.get_detail(link)
                else:
                    self.newsDict['valid'] = False

    def get_detail(self, url):
        print(url)
        r = requests.get(url)
        r.encoding = 'gb2312'
        d = pq(r.text)
        self.newsDict[url]['content'] = d('#contentText p').text()
        self.newsDict[url]['image_links'] = [i.attr('src') for i in d.items('#contentText img')]
        self.newsDict[url]['video_links'] = [i.attr('flashvars') for i in d.items('.video embed')]
        if d('#contentText'):
            self.newsDict[url]['summary'] = d('#description').text()
            source = d('#sourceOrganization').text()
            source_link = d('#isBasedOnUrl').text()
            self.newsDict[url]['source'] = source
            self.newsDict[url]['source_link'] = source_link
        elif d('#contentA'):
            self.newsDict[url]['summary'] = d('h1').text()
            source = d('#media_span').text()
            source_link = d('#media_span a').attr.href
            self.newsDict[url]['source'] = source
            self.newsDict[url]['source_link'] = source_link
        elif d('#contentB'):
            self.newsDict[url]['summary'] = d('h2').text()
            source = d('#media_span').text()
            source_link = d('#contentB .mediasource a').attr.href
            self.newsDict[url]['source'] = source
            self.newsDict[url]['source_link'] = source_link
        else:
            self.newsDict[url]['valid'] = False
            logger.error(url)
            return
        nums = self.get_comment_num(url)
        self.newsDict[url]['comment_num'] = nums[0]
        self.newsDict[url]['reply_num'] = nums[1]

    # http://changyan.sohu.com/api/2/topic/count?client_id=cyqemw6s1&topic_id=415856248
    # {"result":{"415856248":{"comments":63,"id":639793688,"likes":0,"parts":3255,"shares":0,"sid":"415856248","sum":63}}}
    __commentNumUrl = 'http://m.sohu.com/cm/{0}/?_once_=000023_news_v2all&tag=login&_smuid=ABKhOOzrCCTC7fOxhFzzPY&_trans_=000115_3w&v=2'

    def get_comment_num(self, url):
        sid = url.split('.')[-2].split('/')[2].strip('n')
        r = requests.get(self.__commentNumUrl.format(sid), timeout=self.timeout)
        if r.status_code == 200:
            pc = ur'(?<=<span class="c2">)\d+(?=人参与)'
            pr = ur'(?<=<span class="c3">\[1/)\d+(?=])'
            mc = re.search(pc, r.text)
            if (not mc) or mc.group() == '0':
                return '0', '0'
            mr = re.search(pr, r.text)
            if not mr:
                return mc.group(), '0'
            if mr.group() == '1':
                return mc.group(), str(r.text.count(u'<div class="w1 bd3">'))
            replynum = int(mr.group()) * 5
            return mc.group(), str(replynum)
        else:
            return '0', '0'

    def save_by_day(self, date_str):
        connect('sohu')
        for k in self.newsDict:
            if not self.newsDict[k]['valid']:
                error = ErrorArticle(link=self.newsDict[k]['link'], title=self.newsDict[k]['title'], post_date=date_str)
                error.post_time = self.newsDict[k]['post_time']
                error.category = self.newsDict[k]['category']
                error.count = 1
                error.save()
                continue
            article = Article(link=self.newsDict[k]['link'], title=self.newsDict[k]['title'], post_date=date_str)
            article.post_time = self.newsDict[k]['post_time']
            article.category = self.newsDict[k]['category']
            article.summary = self.newsDict[k]['summary']
            article.source = self.newsDict[k]['source']
            article.source_link = self.newsDict[k]['source_link']
            article.content = self.newsDict[k]['content']
            article.image_links = self.newsDict[k]['image_links']
            article.video_links = self.newsDict[k]['video_links']
            article.comment_num = self.newsDict[k]['comment_num']
            article.reply_num = self.newsDict[k]['reply_num']
            article.save()

    def reget_errorlist(self):
        print '###############'
        for item in ErrorArticle.objects:
            print item.count
