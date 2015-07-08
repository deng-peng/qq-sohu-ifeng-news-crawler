# -*- encoding: utf-8 -*
import logging
import time

import requests

from pyquery import PyQuery as pq

from worker import *
from article import *
from logger import Logger

logger = Logger(logname='ifeng.log', logger=__name__).get_logger()


class FengWorker(Worker):
    def __init__(self, startdate=date(2010, 1, 1), enddate=date(2015, 6, 5)):
        super(FengWorker, self).__init__()
        self.beginDate = startdate
        self.endDate = enddate

    # http://news.ifeng.com/listpage/11528/20150311/2/rtlist.shtml
    # 大陆 11528 国际 11574 即时 11502
    __listUrl = 'http://news.ifeng.com/listpage/{0}/{1}/{2}/rtlist.shtml'
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
            catg = {'11528': '大陆', '11574': '国际', '11502': '即时'}
            for ct in catg.keys():
                page = 1
                # 当日首页
                r = requests.get(self.__listUrl.format(ct, date_str, page))
                if r.status_code == 200:
                    d = pq(r.text)
                    self.parse_articles_list(d('.newsList'), date_str, catg[ct])
                    # 循环分页
                    while len(d('.newsList ul li')) == 60:
                        page += 1
                        r = requests.get(self.__listUrl.format(ct, date_str, page))
                        d = pq(r.text)
                        self.parse_articles_list(d('.newsList'), date_str, catg[ct])
            self.save_temp_dict()
        except StandardError, e:
            logging.exception(date_str + ' error', e)
        finally:
            self.newsDict.clear()

    def parse_articles_list(self, articles, post_date, category):
        d = pq(articles)
        for i in range(0, d('ul li').length):
            li = d('ul li').eq(i)
            title = li('li a').text()
            link = li('li a').attr('href')
            timestr = li('h4').text()
            post_time = timestr.split(' ')[1]
            item = {'title': title, 'link': link, 'post_date': post_date, 'category': category,
                    'post_time': post_time, 'valid': True, 'error_count': 0}
            self.newsDict[link] = item
            # 重试
            retry = 3
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
            # 非正常结果抛出异常
            if r.status_code == 404:
                self.newsDict[url]['valid'] = False
                logger.info('404 page not found')
                return True
            r.raise_for_status()
            # r.encoding = 'utf-8'
            d = pq(r.text)
            d('.ifengLogo').remove()
            d('script').remove()
            source = ''
            source_link = ''
            if d('[itemprop=description]'):
                self.newsDict[url]['summary'] = d('[itemprop=description]').attr('content')
            elif d('[name=description]'):
                self.newsDict[url]['summary'] = d('[name=description]').attr('content')
            else:
                self.newsDict[url]['summary'] = ''
            self.newsDict[url]['content'] = d('#main_content p').text()
            if len(self.newsDict[url]['content']) == 0:
                self.newsDict[url]['content'] = d('#artical_real p').text()
            self.newsDict[url]['image_links'] = [i.attr('src') for i in d.items('#artical_real p img')]
            self.newsDict[url]['video_links'] = ['http://v.ifeng.com/include/exterior.swf?' + i.attr('flashvars') for i in
                                                 d.items('#artical_real object embed')]
            if d('#source_place'):
                self.newsDict[url]['source'] = d('#source_place').text()
                if d('#source_place a'):
                    source_link = d('#source_place a').attr.href
                self.newsDict[url]['source_link'] = source_link
            elif d('#artical_sth > p > span:nth-child(3)'):
                self.newsDict[url]['source'] = d('#artical_sth > p > span:nth-child(3)').text()
                if d('#artical_sth > p > span:nth-child(3) a'):
                    source_link = d('#artical_sth > p > span:nth-child(3) a').attr.href
                self.newsDict[url]['source_link'] = source_link
            elif d('#artical_real'):
                if d('#artical_sth .ss03 a'):
                    source = d('#artical_sth .ss03 a').text()
                    source_link = d('#artical_sth .ss03 a').attr.href
                self.newsDict[url]['source'] = source
                self.newsDict[url]['source_link'] = source_link
            else:
                self.newsDict[url]['valid'] = False
                logger.error('check url :' + url)
                return False
            nums = self.get_comment_num(url)
            self.newsDict[url]['comment_num'] = nums[0]
            self.newsDict[url]['reply_num'] = nums[1]
            return True
        except StandardError:
            logger.error('get detail error :' + url)
            return False

    # http://comment.ifeng.com/joincount.php?doc_url=http%3A%2F%2Fnews.ifeng.com%2Fa%2F20150623%2F44022615_0.shtml&format=js&callback=callbackGetFastCommentCount
    __commentNumUrl = 'http://comment.ifeng.com/joincount.php'

    def get_comment_num(self, url):
        payload = {'doc_url': url, 'format': 'js', 'callback': 'callbackGetFastCommentCount'}
        r = requests.get(self.__commentNumUrl, params=payload)
        if r.text.startswith('callbackGetFastCommentCount'):
            cont = get_content_between(r.text, '(', ')')
            nums = cont.split(',')
            if len(nums) > 1:
                return nums[0], nums[1]
            else:
                return nums[0], '0'
        else:
            return '0', '0'
