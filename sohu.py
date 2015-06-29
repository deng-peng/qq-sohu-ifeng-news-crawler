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
            item = articles[i].strip('[]').split(',')
            category = ''
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

    def get_detail(self, url):
        print(url)
        r = requests.get(url)
        r.encoding = 'utf-8'
        d = pq(r.text)
        source = ''
        source_link = ''
        self.newsDict[url]['content'] = d('#contentText').text()
        self.newsDict[url]['image_links'] = [i.attr('src') for i in d.items('#contentText img')]
        self.newsDict[url]['video_links'] = [i.attr('flashvars') for i in d.items('#sohuplayer embed')]
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
        sid = get_content_between(r.text, 'var newsId = ', ';')
        if sid != '':
            nums = self.get_comment_num_new(sid)
            self.newsDict[url]['comment_num'] = nums[0]
            self.newsDict[url]['reply_num'] = nums[1]
        else:
            self.newsDict[url]['comment_num'] = '0'
            self.newsDict[url]['reply_num'] = '0'

    # http://changyan.sohu.com/api/2/topic/count?client_id=cyqemw6s1&topic_id=415856248
    # {"result":{"415856248":{"comments":63,"id":639793688,"likes":0,"parts":3255,"shares":0,"sid":"415856248","sum":63}}}
    __commentNumUrl = 'http://changyan.sohu.com/api/2/topic/count?client_id=cyqemw6s1&topic_id={0}'

    def get_comment_num(self, sid):
        r = requests.get(self.__commentNumUrl.format(sid), timeout=self.timeout)
        if r.status_code == 200:
            j = r.json()
            jj = j['result'][sid]
            return str(jj['comments']), str(jj['parts'])
        else:
            return '0', '0'

    def save_by_day(self, date_str):
        connect('sohu')
        for k in self.newsDict:
            if not self.newsDict[k]['valid']:
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
