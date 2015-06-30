# -*- encoding: utf-8 -*
from mongoengine import *


class Article(Document):
    # 链接
    link = StringField(required=True)
    # 标题
    title = StringField()
    # 发布日期
    post_date = StringField()
    # 发布时间
    post_time = StringField()
    # 分类
    category = StringField()
    # 来源
    source = StringField()
    # 来源链接
    source_link = StringField()
    # 导语
    summary = StringField()
    # 正文
    content = StringField()
    # 正文图片(只要链接)
    image_links = ListField(StringField())
    # 视频(只要链接)
    video_links = ListField(StringField())
    # 评论数量
    comment_num = StringField()
    # 参与数量(新版的评论包括参与数量和评论数量,两个都需要;老版的可能没有参与数量)
    reply_num = StringField()


class ErrorArticle(Document):
    # 链接
    link = StringField(required=True)
    # 标题
    title = StringField()
    # 发布日期
    post_date = StringField()
    # 发布时间
    post_time = StringField()
    # 分类
    category = StringField()
    # 错误次数
    count = IntField()
