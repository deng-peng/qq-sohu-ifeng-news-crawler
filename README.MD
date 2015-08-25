##简介
抓取腾讯新闻，搜狐新闻和凤凰网新闻

##部署说明
1、使用了3个第三方库

* pip install requests
* pip install pyquery ///这个如果安装失败，可能需要apt-get install libxml2-dev libxslt1-dev python-dev
* pip install mongoengine ///如果连接数据库失败，可能是兼容性问题，可以卸载 pip uninstall pymongo 后安装指定版本 pip install pymongo==2.8

2、抓取日期配置在各个源文件中的__init__写有默认值。其中qq和sohu的在网页可以看到最早的日期，凤凰网可以获取到很早的列表，但是基本都是404页面

3、运行可以通过 python start.py qq / python start.py sohu /python start.py ifeng，可以指定分类。也可以指定时间段 python start.py qq 2011-01-02 2013-03-04

4、程序逻辑简介：

* 按照日为最小存储单位，取满一整天的所有数据，才会去数据库存储一次,如果中间出现什么未捕获的异常，当天的数据就不会存储，下次重新再抓。
* 如果某一日中的某些文章获取不正常被捕获，这些文章的url和列表参数会存储到一个failed的集合中，以后每次运行程序会重新处理一次这些数据，多次失败后不再重试。
* 启动时会查询所有抓取过的日期，已经处理的日期就不再抓取，但是之前出错的url会再次重试。因为这个机制，不要抓取今日的数据，最晚到昨天。
* 程序里大部分地方都有重试，qq和sohu为1次，凤凰网经常报错，设为3次。超时设为30秒
