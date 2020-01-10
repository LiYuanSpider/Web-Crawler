import time
import re
from threading import Thread
import requests
from scrapy import Selector
from csdn_spider import *
from csdn_spider.models import *
from urllib import parse
from datetime import datetime
from csdn_spider.spider import *
from queue import Queue


# 网页url地址
domain = 'https://bbs.csdn.net'

# 设置全局变量 注意：Python中是共享全局变量
topic_list_queue = Queue()
topic_queue = Queue()
author_queue = Queue()

class ParseTopicDetailThread(Thread):
    def run(self):
        while True:
            url = topic_queue.get()
            print("开始获取帖子：{}",format(url))
            print(url)
            # 获取作者id
            topic_id = url.split("/")[-1]
            # 获取详情页内容
            res_text = requests.get(url).text
            sel = Selector(res_text)
            # 获取内容 注意：在解析数据的时候，查看是否是静态、动态 方法：直接查看网页源代码和element中的的元素对比
            content = sel.xpath("//div[@class='post_body post_body_min_h']").extract()[0]
            # 获取或赞数
            praised_nums = sel.xpath("//div[@class='control_l fl']/label[@class='red_praise digg']/em/text()").extract[
                0]
            # 获取结帖率 去掉空格
            jt1_str = sel.xpath("//div[@class='close_topic']//text()").extract()[0].split()
            # 使用正则表达式提取数值
            jt1 = 0
            jt1_match = re.search("(\d+)%", jt1_str)
            if jt1_match:
                jt1 = int(jt1_match.group(1))
            # 获取作者信息
            author_info = sel.xpath("//div[@class='user_nick_name']//a[1]/@href").extract()[0]
            # 获取作者id
            author_id = author_info.split("/")[-1]
            # 获取创建时间
            create_time = sel.xpath("//label[@class='date_time']/text()").extract()[0]
            # 格式化时间
            create_time = datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S")

            # 创建实例对象
            answer = Answer()
            existed_topics = Topic.select().where(Topic.id == topic_id)
            if existed_topics:
                # 向表中插入数据
                answer.topic_id = topic_id
                answer.author = author_id
                answer.content = content
                answer.create_time = create_time
                answer.praised_nums = int(praised_nums)
                # 提交数据
                answer.save()

            # 获取下一页的url 注意：查看对应的class标签是否是全局唯一的
            next_page = sel.xpath("//div/a[10]/@href").extract()
            if next_page:
                topic_list_queue.put(next_page)

# 使用类构建多线程
class ParseTopicList(Thread):
    def run(self):
        while True:
            try:
                url = topic_list_queue.pop()
            except IndexError as e:
                time.sleep(1)
                continue
            print("开始获取帖子列表页：{}".format(url))
            print(url)
            # 获取对应的数据页面内容 注意：此处需要增加反爬机制
            res_text = requests.get(url).text
            # 使用Xpath规则进行解析
            sel = Selector(text=res_text)
            # 匹配列表页（待解决）中的列表 注意：直接拷贝Xpath存在问题就是通用性不强
            all_sel = sel.xpath('//table[@class="forums_tab_table"]/tbody//tr')
            # 遍历每个url 注意：匹配原则能够匹配列表也数据，就不要去详情页
            for tr in all_sel:
                # 获取列表信息的状态 注意：选取准确值，只有在确保有值的情况下才不会报错
                status = tr.xpath(".//td[1]/span/text()").extract()[0]
                # 获取列表信息得分
                score = tr.xpath(".//td[2]/em/text()").extract()[0]
                # 获取列表主题信息的url
                topic_url = parse.urljoin(domain, tr.xpath(".//td[3]/a/@href").extract()[0])
                # 获取列表主题
                topic_title = tr.xpath(".//td[3]/a/text()").extract()[0]
                # 获取作者的url信息
                author_url = parse.urljoin(domain, tr.xpath(".//td[4]/a/@href").extract()[0])
                # 获取用户的id
                author_id = author_url.split("/")[-1]
                # 获取回复和查看数量
                answer_info = tr.xpath(".//td[5]/span/text()").extract()[0]
                # 获取创建时间
                create_time = tr.xpath(".//td[4]/em/text()").extract()[0]
                # 将获取到的创建时间转换为格式化日期
                create_time = datetime.strptime(create_time, "%Y-%m-%d %H:%M")
                # 获取回复数量
                answer_nums = answer_info.split("/")[0]
                # 获取查看数量
                click_nums = answer_info.split("/")[1]
                # 获取最后的回复时间
                last_time_str = tr.xpath(".//td[6]/em/text()").extract()[0]
                # 将时间转换为datetime的字段
                last_time = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M")

                # 创建实例对象
                topic = Topic()
                # 注意保存数据到数据库中，如果没有设置默认值，如果爬取的数据不存在将会报错
                topic.id = int(topic_url.split("/")[-1])
                topic.title = topic_title
                topic.author = author_id
                topic.click_nums = int(click_nums)
                topic.answer_nums = int(answer_nums)
                topic.create_time = create_time
                topic.last_answer_time = last_time
                topic.score = score
                topic.status = status

                # 数据去重的一种方式：使用主键来达到去重
                existed_topics = Topic.select().where(Topic.id == topic.id)
                if existed_topics:
                    # 直接保存数据
                    topic.save()
                else:
                    # 使用save方法插入数据
                    topic.save(force_insert=True)  # 数据存在更新，不存在插入

                # 调用解析帖子详情页的函数
                topic_queue.put(topic_url)
                # 调用解析作者详情页的函数
                # parse_author(author_url)

            # 获取下一页的url 注意：查看对应的class标签是否是全局唯一的
            next_page = sel.xpath("//div/a[10]/@href").extract()
            # 判断是否提取数据到最后一页
            if next_page:
                topic_queue.put(next_page)


class ParseAuthorThread(Thread):
    def run(self):
        while True:
            try:
                url = author_queue.get()
            except IndexError as e:
                time.sleep(1)
                continue
            print("开始获取帖子：{}".format(url))
            print(url)
            # 请求用户网页详情 注意：反爬设置
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36"
            }
            res_text = requests.get(url, headers=headers).text
            sel = Selector(text=res_text)
            name = sel.xpath("//div[@class='lt_main clearfix']/p/text()").extract()[2].strip()
            # 此部分还需要扩展

if __name__ == '__main__':
    """
    # 1、将获取初始（导航栏）的url放入一个单独的线程去完成
    # 2、如何去停止线程
    # 1、我们手动停止 ctrl+c
       # 1、接收ctrl+c
       # 2、保存变量
       # 3、下一次启动程序的时候，我们应该如何从文件中（mysql）启动
    # 2、程序有可能直接崩溃
       # 1、queue是内存中的，是否安全
       # 2、queue这种模式就不合适了，使用mysql来进行同步
       # 3、redis
   # 3、爬虫完成后的退出
       # 1、如何去判断爬虫数据已经抓取完成了
   # 积极思考如何改进业务
    """
    last_urls = get_last_list()
    for url in last_urls:
        topic_list_queue.put(url)

    topic_list_thread = ParseTopicDetailThread()
    topic_detail_thread = ParseTopicDetailThread()
    parse_author_Thread = ParseTopicDetailThread()

    topic_list_thread.start()
    topic_detail_thread.start()
    parse_author_Thread.start()