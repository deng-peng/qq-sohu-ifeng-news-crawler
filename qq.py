# -*- encoding: utf-8 -*
import random
import requests
from pyquery import PyQuery as pq
import time
from logger import Logger
from worker import *
from article import *
from mongoengine import *

logger = Logger(logname='qq.log', logger=__name__).get_logger()


class QqWorker(Worker):
    def __init__(self, startdate=date(2010, 3, 1), enddate=date(2010, 3, 5)):
        super(QqWorker, self).__init__()
        self.beginDate = startdate
        self.endDate = enddate
        self.dbName = 'qq'

    # http://roll.news.qq.com/interface/roll.php?0.3343920919516311&cata=&site=news&date=2009-01-01&page=1&mode=2&of=json
    #           国内 newsgn 国际 newsgj 社会 newssh
    __listUrl = 'http://roll.news.qq.com/interface/roll.php?{0}&cata={1}&site=news&date={2}&page={3}&mode=2&of=json'
    __referUrl = 'http://roll.news.qq.com/index.htm?site=news&mod=2&date={0}&cata='

    def start(self):
        self.get_records()
        catg = ['newsgn', 'newsgj', 'newssh']
        for ct in catg:
            day = self.beginDate
            while day <= self.endDate:
                if day not in self.historyDict:
                    self.crawl_by_day(day, ct)
                day += Worker.dayDelta

    def get_records(self):
        connect(self.dbName)
        self.history = Article.objects.distinct('post_date')

    def crawl_by_day(self, day, catg):
        page = 1
        date_str = day.strftime("%Y-%m-%d")
        random_str = random.random()
        headers = {'Referer': self.__referUrl.format(date_str)}
        # 当日首页
        try:
            res = requests.get(self.__listUrl.format(random_str, catg, date_str, page), headers=headers,
                               timeout=self.timeout)
            jo = res.json()
            responsecode = jo['response']['code']
            if responsecode == '0':
                pagecount = jo['data']['count']
                articles = jo['data']['article_info']
                self.parse_articles_list(articles)
                # 循环分页
                while page < pagecount:
                    page += 1
                    res = requests.get(self.__listUrl.format(random_str, date_str, page), headers=headers,
                                       timeout=self.timeout)
                    jo = res.json()
                    articles = jo['data']['article_info']
                    self.parse_articles_list(articles)
                self.save_by_day(date_str)
        except requests.exceptions.RequestException, e:
            logger.exception(e)
        except StandardError, e:
            logger.error(date_str + ' error')
            logger.exception(e)

    def parse_articles_list(self, articles):
        doc = pq(articles)
        for i in range(1, doc('div').length):
            div = doc('div').eq(i)
            title = div('dt a').text()
            category = div('.t-tit').text().strip('[]')
            itemstr = div('.t-time').text()
            post_time = itemstr.split(' ')[1]
            link = div('dt a').attr('href')
            # 丢掉阅读全文几个字
            div('dl dd a').empty()
            summary = div('dl dd').text()
            item = {'title': title, 'summary': summary, 'link': link, 'category': category, 'post_time': post_time,
                    'valid': True}
            self.newsDict[link] = item
            # 重试
            retry = 1
            try:
                self.get_detail(link)
            except StandardError:
                if retry > 0:
                    retry -= 1
                    time.sleep(5)
                    self.get_detail(link)
                else:
                    self.newsDict[link]['valid'] = False

    def get_detail(self, url):
        logger.info(url)
        r = requests.get(url, timeout=self.timeout)
        d = pq(r.text)
        source = ''
        source_link = ''
        cmt_id = ''
        if d('#ArticleCnt'):
            if len(d('#ArtFrom a')) > 2:
                source = d('#ArtFrom a').eq(1).text()
                source_link = d('#ArtFrom a').eq(1).attr('href')
            self.newsDict[url]['source'] = source
            self.newsDict[url]['source_link'] = source_link
            self.newsDict[url]['content'] = d('#ArticleCnt p').text()
            cmt_id = get_content_between(d.html(), 'cmt_id = ', ';')
            self.newsDict[url]['image_links'] = [i.attr('src') for i in d.items('#ArticleCnt p img')]
            self.newsDict[url]['video_links'] = ['http://static.video.qq.com/TPout.swf?' + i.attr('flashvars') for i in
                                                 d.items('#ArticleCnt OBJECT embed')]
            # 文章内有分页的情况
            if d('#ArticlePageLinkB'):
                try:
                    pgs = len(d('#ArticlePageLinkB a'))
                    for p in range(1, pgs):
                        innerurl = url.replace('.htm', '_' + p + '.htm')
                        rr = requests.get(innerurl, timeout=self.timeout)
                        dd = pq(rr.text)
                        if dd('#ArticleCnt'):
                            self.newsDict[url]['content'] += dd('#ArticleCnt p').text()
                            self.newsDict[url]['image_links'] += [i.attr('src') for i in dd.items('#ArticleCnt p img')]
                            self.newsDict[url]['video_links'] += [
                                'http://static.video.qq.com/TPout.swf?' + i.attr('flashvars') for i in
                                dd.items('#ArticleCnt OBJECT embed')]
                except StandardError, e:
                    logger.error(url + ' error')
                    logger.exception(e)
        elif d('#C-Main-Article-QQ'):
            if d('#C-Main-Article-QQ .tit-bar .color-a-1'):
                source = d('#C-Main-Article-QQ .tit-bar .color-a-1').text()
            elif d('#C-Main-Article-QQ .infoCol .where'):
                source = d('#C-Main-Article-QQ .infoCol .where').text()
            if d('#C-Main-Article-QQ .tit-bar .color-a-1 a'):
                source_link = d('#C-Main-Article-QQ .tit-bar .color-a-1 a').attr('href')
            elif d('#C-Main-Article-QQ .infoCol .where a'):
                source_link = d('#C-Main-Article-QQ .infoCol .where a').attr('href')

            self.newsDict[url]['source'] = source
            self.newsDict[url]['source_link'] = source_link
            self.newsDict[url]['content'] = d('#Cnt-Main-Article-QQ p').text()
            cmt_id = get_content_between(d.html(), 'cmt_id = ', ';')
            self.newsDict[url]['image_links'] = [i.attr('src') for i in d.items('#Cnt-Main-Article-QQ p img')]
            self.newsDict[url]['video_links'] = ['http://static.video.qq.com/TPout.swf?' + i.attr('flashvars') for i in
                                                 d.items('#mod_player embed')]
            # 文章内有分页的情况
            # if d('#ArticlePageLinkB'):
            #     try:
            #         pgs = len(d('#ArticlePageLinkB a'))
            #         for p in range(1, pgs):
            #             innerurl = url.replace('.htm', '_' + p + '.htm')
            #             rr = requests.get(innerurl, timeout=self.timeout)
            #             dd = pq(rr.text)
            #             if dd('#C-Main-Article-QQ'):
            #                 self.newsDict[url]['content'] += dd('#Cnt-Main-Article-QQ p').text()
            #                 self.newsDict[url]['image_links'] += [i.attr('src') for i in
            #                                                       dd.items('#Cnt-Main-Article-QQ p img')]
            #                 self.newsDict[url]['video_links'] += [
            #                     'http://static.video.qq.com/TPout.swf?' + i.attr('flashvars') for i in
            #                     dd.items('#mod_player embed')]
            #     except StandardError, e:
            #         logger.error(url + ' error')
            #         logger.exception(e)
        else:
            self.newsDict[url]['valid'] = False
            logger.error(url)
            return
        if cmt_id != '':
            if int(cmt_id) < 100000000:
                nums = self.get_comment_num(cmt_id)
            else:
                nums = self.get_comment_num_new(cmt_id)
            self.newsDict[url]['comment_num'] = nums[0]
            self.newsDict[url]['reply_num'] = nums[1]
        else:
            self.newsDict[url]['comment_num'] = '0'
            self.newsDict[url]['reply_num'] = '0'

    __commentNumUrl = 'http://sum.comment.gtimg.com.cn/php_qqcom/gsum.php?site=news&c_id={0}'

    def get_comment_num(self, cmt_id):
        r = requests.get(self.__commentNumUrl.format(cmt_id), timeout=self.timeout)
        if r.text.startswith('_cbSum'):
            cont = get_content_between(r.text, '(', ')')
            nums = cont.split(',')
            if len(nums) > 1:
                return nums[0], nums[1]
            else:
                return nums[0], '0'
        else:
            return '0', '0'

    __commentNumUrlNew = 'http://coral.qq.com/article/{0}/commentnum'

    # 新版没有参与数
    def get_comment_num_new(self, cmt_id):
        headers = {'User-Agent': 'Chrome/44.0.2403.39 Safari/537.36'}
        r = requests.get(self.__commentNumUrlNew.format(cmt_id), headers=headers, timeout=self.timeout)
        jo = r.json()
        if jo['errCode'] == 0:
            return str(jo['data']['commentnum']), '0'
        else:
            return '0' '0'

    def save_by_day(self, date_str):
        connect(self.dbName)
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
