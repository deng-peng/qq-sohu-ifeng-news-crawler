# -*- encoding: utf-8 -*
import logging
import re
import requests
import time
from pyquery import PyQuery as pq
from worker import *
from article import *
from logger import Logger

logger = Logger(logname='sohu.log', logger=__name__).get_logger()


class SohuWorker(Worker):
    def __init__(self, startdate=date(2009, 7, 13), enddate=date(2015, 6, 1)):
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
            date_str = day.strftime("%Y%m%d")
            if date_str not in self.history:
                self.crawl_by_day(date_str)
            day += Worker.dayDelta
        self.reget_errorlist()

    def get_records(self):
        self.history = Article.objects.distinct('post_date')

    def crawl_by_day(self, date_str):
        try:
            r = requests.get(self.__listUrl.format(date_str))
            r.encoding = 'utf-8'
            reg = re.compile(r'\[\d,.*?]')
            if r.status_code == 200:
                items = reg.findall(r.text)
                if len(items) > 0:
                    self.parse_articles_list(items, date_str)
                    self.save_temp_dict()
        except StandardError, e:
            logger.exception(date_str + ' error', e)
        finally:
            self.newsDict.clear()

    def parse_articles_list(self, articles, post_date):
        for i in range(len(articles)):
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
            if not link.startswith('http://news.sohu.com'):
                continue
            post_time = item[3].split(' ')[1].rstrip('"')
            item = {'title': title, 'link': link, 'post_date': post_date, 'post_time': post_time, 'category': category,
                    'valid': True, 'error_count': 0}
            self.newsDict[link] = item
            # 重试
            retry = 1
            while not self.get_detail(link):
                if retry <= 0:
                    self.newsDict[link]['valid'] = False
                    break
                else:
                    retry -= 1
                    time.sleep(1)

    def get_detail(self, url):
        logger.info(url)
        try:
            r = requests.get(url)
            r.raise_for_status()
            r.encoding = 'gb2312'
            d = pq(r.text)
            d('script').remove()
            d('.newsComment').remove()
            content = d('div[itemprop=articleBody]').text()
            if len(content) == 0:
                content = d('#contentText p').text()
            if len(content) == 0:
                d('#contentText .r').remove()
                content = d('#contentText').text()
            if len(content) == 0:
                content = d('#sohu_content').text()
            if len(content) == 0:
                content = d('.content').text()
            self.newsDict[url]['content'] = content
            self.newsDict[url]['image_links'] = [i.attr('src') for i in d.items('#contentText img')]
            self.newsDict[url]['video_links'] = [
                i.attr('src') if i.attr('src').startswith('http://share.vrs.sohu.com')
                else i.attr('flashvars') for i in d.items('embed')]
            if d('#description'):
                self.newsDict[url]['summary'] = d('#description').text()
                self.newsDict[url]['source'] = d('#sourceOrganization').text()
                self.newsDict[url]['source_link'] = d('#isBasedOnUrl').text()
            elif d('#media_span'):
                self.newsDict[url]['summary'] = self.newsDict[url]['title']
                self.newsDict[url]['source'] = d('#media_span').text()
                source_link = d('#media_span a').attr.href
                if (not source_link) or len(source_link) == 0:
                    source_link = d('.mediasource a').attr.href
                if (not source_link) or len(source_link) == 0:
                    source_link = ''
                self.newsDict[url]['source_link'] = source_link
            else:
                self.newsDict[url]['summary'] = self.newsDict[url]['title']
                self.newsDict[url]['source'] = ''
                self.newsDict[url]['source_link'] = ''
            nums = self.get_comment_num(url)
            self.newsDict[url]['comment_num'] = nums[0]
            self.newsDict[url]['reply_num'] = nums[1]
            return True
        except StandardError, e:
            logger.exception('get detail error:' + url, e)
            return False

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

