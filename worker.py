# -*- encoding: utf-8 -*
from datetime import timedelta, date
from article import Failed, Article


def get_content_between(src, starttag, endtag):
    si = src.find(starttag)
    if si >= 0:
        sii = si + len(starttag)
        se = src.find(endtag, si)
        if se > sii:
            return src[sii: se]
    return ''


class Worker(object):
    dayDelta = timedelta(days=30)
    timeout = 30

    def __init__(self):
        self.newsDict = {}
        self.history = {}

    def save_temp_dict(self):
        for k in self.newsDict:
            if not self.newsDict[k]['valid']:
                error = Failed(link=self.newsDict[k]['link'], title=self.newsDict[k]['title'],
                               post_date=self.newsDict[k]['post_date'])
                error.post_time = self.newsDict[k]['post_time']
                error.category = self.newsDict[k]['category']
                error.summary = self.newsDict[k]['summary']
                error.error_count = self.newsDict[k]['error_count'] + 1
                error.save()
                continue
            article = Article(link=self.newsDict[k]['link'], title=self.newsDict[k]['title'],
                              post_date=self.newsDict[k]['post_date'])
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
            if self.newsDict[k]['error_count'] > 0:
                Failed.objects(link=self.newsDict[k]['link']).delete()

    def reget_errorlist(self):
        print('#### reget error list ####')
        # 错误多次的不再重试
        for item in Failed.objects(error_count__lte=5):
            print(item.link)
            self.newsDict[item.link] = {'title': item.title, 'link': item.link, 'post_time': item.post_time,
                                        'post_date': item.post_date, 'category': item.category, 'summary': item.summary,
                                        'valid': True, 'error_count': item.error_count}
            try:
                self.get_detail(item.link)
            except StandardError:
                self.newsDict['valid'] = False
            self.save_temp_dict()
        print('#### end ####')
