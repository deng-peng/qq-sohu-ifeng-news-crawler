# -*- encoding: utf-8 -*
from datetime import date, timedelta

def get_content_between(src, starttag, endtag):
    si = src.find(starttag)
    if si >= 0:
        sii = si + len(starttag)
        se = src.find(endtag, si)
        if se > sii:
            return src[sii: se]
    return ''


class Worker(object):
    dayDelta = timedelta(days=1)

    def __init__(self):
        self.newsDict = {}
        self.historyDict = {}

