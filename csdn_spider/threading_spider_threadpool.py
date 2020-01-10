"""
系统的整体：1、抓取 2、解析 3、存储
"""
import re
import ast
from urllib import parse
import requests
from datetime import datetime
from scrapy import Selector
import json
import time
from csdn_spider.models import *
from csdn_spider.models import *

domain = 'https://bbs.csdn.net'
# 在线获取字符串
def get_nodes_json():
    # 获取js的文本
    left_menu_text = requests.get('https://bbs.csdn.net/dynamic_js/left_menu.js?csdn').text
    # 输出测试信息
    # print(left_menu_text)
    # 正则表达式匹配对应数据 注意点：1、结构化数据和非结构数据提取 2、js数据null和Python中的json数据中None的相互转换
    nodes_str_match = re.search('forumNodes: (.*])',left_menu_text)
    # 提取到数据
    if nodes_str_match:
        # 对提取到的数据进行处理、清洗，去除null的值采用None进行替代
        nodes_str = nodes_str_match.group(1).replace('null','None')
        # 将对应的字符串转换为列表
        nodes_list = ast.literal_eval(nodes_str)
        # 输出测试信息
        # print(nodes_list)
        return nodes_list
    return []


url_list = []
# 对获取到的nodes_list进一步处理l'y'ton
def process_nodes_list(nodes_list):
    # 将js的格式提取出url转换到list中
    for item in nodes_list:
        if 'url' in item:
            if item['url']:
                url_list.append(item['url'])
            if 'children' in item:
                process_nodes_list(item['children'])


# 减少重复的url
def get_levell_list(nodes_list):
    # 定义一个空的列表
    levell_url = []
    # 遍历列表元素
    for item in nodes_list:
        # 判断url是否在第一层中，并且url对应的内容存在
        if 'url' in item and item['url']:
            # 将第一层的url提取出来，并且添加到对应的列表中
            levell_url.append(item['url'])
    return levell_url


# 获取最后需要抓取的url 包括：推荐精华、已解决和待解决（主列表页）
def get_last_list():
    # 获取js加载的链接
    nodes_list = get_nodes_json()
    # 获取所有的链接列表
    process_nodes_list(nodes_list)
    # 获取第一层的链接
    levell_url = get_levell_list(nodes_list)
    # 存储最后爬取的链接
    last_urls = []
    # 遍历所有的链接
    for url in url_list:
        # 判断链接是否存在在第一层中
        if url not in levell_url:
            # 存储最终要爬取的链接
            last_urls.append(url)
    # 存储所有的url
    all_urls = []
    # 判断链接是否在最终的链接中
    for url in last_urls:
        # 拼接成完整的url 注意：推荐精华、已解决和待解决（主列表页）中url的细微区别
        all_urls.append(parse.urljoin(domain, url+'/recommend'))
        all_urls.append(parse.urljoin(domain,url+"closed"))
        all_urls.append(parse.urljoin(domain, url))
    return all_urls


# 获取列表页数据 包括：列表页、推荐精华、已解决和待解决
def parse_list(url):
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
        topic_url = parse.urljoin(domain,tr.xpath(".//td[3]/a/@href").extract()[0])
        # 获取列表主题
        topic_title = tr.xpath(".//td[3]/a/text()").extract()[0]
        # 获取作者的url信息
        author_url = parse.urljoin(domain,tr.xpath(".//td[4]/a/@href").extract()[0])
        # 获取用户的id
        author_id = author_url.split("/")[-1]
        # 获取回复和查看数量
        answer_info = tr.xpath(".//td[5]/span/text()").extract()[0]
        # 获取创建时间
        create_time = tr.xpath(".//td[4]/em/text()").extract()[0]
        # 将获取到的创建时间转换为格式化日期
        create_time = datetime.strptime(create_time,"%Y-%m-%d %H:%M")
        # 获取回复数量
        answer_nums = answer_info.split("/")[0]
        # 获取查看数量
        click_nums = answer_info.split("/")[1]
        # 获取最后的回复时间
        last_time_str = tr.xpath(".//td[6]/em/text()").extract()[0]
        # 将时间转换为datetime的字段
        last_time = datetime.strptime(last_time_str,"%Y-%m-%d %H:%M")

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
            topic.save(force_insert=True) # 数据存在更新，不存在插入

        # 调用解析帖子详情页的函数
        # parse_topic(topic_url)
        executor.submit(parse_topic,topic_url)
        executor.submit(parse_author,author_url)
        # 调用解析作者详情页的函数
        # parse_author(author_url)
    
    # 获取下一页的url 注意：查看对应的class标签是否是全局唯一的
    next_page = sel.xpath("//div/a[10]/@href").extract()   
    # 判断是否提取数据到最后一页
    if next_page:
        # 拼接完整url 
        next_url = parse.urljoin(domain,next_page[0])
        # 重复解析下一列表页
        # parse_list(next_url)
        executor.submit(parse_list,next_url)

# 获取帖子的详情页和回复
def parse_topic(url):
    # 获取作者id
    topic_id = url.split("/")[-1]
    # 获取详情页内容
    res_text = requests.get(url).text
    sel = Selector(res_text)
    # 获取内容 注意：在解析数据的时候，查看是否是静态、动态 方法：直接查看网页源代码和element中的的元素对比
    content = sel.xpath("//div[@class='post_body post_body_min_h']").extract()[0]
    # 获取或赞数
    praised_nums = sel.xpath("//div[@class='control_l fl']/label[@class='red_praise digg']/em/text()").extract[0]
    # 获取结帖率 去掉空格
    jt1_str= sel.xpath("//div[@class='close_topic']//text()").extract()[0].split()
    # 使用正则表达式提取数值
    jt1 = 0
    jt1_match = re.search("(\d+)%",jt1_str)
    if jt1_match:
        jt1 = int(jt1_match.group(1))
    # 获取作者信息
    author_info = sel.xpath("//div[@class='user_nick_name']//a[1]/@href").extract()[0]
    # 获取作者id
    author_id = author_info.split("/")[-1]
    # 获取创建时间
    create_time = sel.xpath("//label[@class='date_time']/text()").extract()[0]
    # 格式化时间
    create_time = datetime.strptime(create_time,"%Y-%m-%d %H:%M:%S")

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
    # 判断是否提取数据到最后一页
    if next_page:
        # 拼接完整url
        next_url = parse.urljoin(domain, next_page[0])
        # 重复解析下一列表页
        # parse_topic(next_url)
        executor.submit(parse_topic)

# 获取用户的详情页
def parse_author(url):
    # 请求用户网页详情 注意：反爬设置
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36"
    }
    res_text = requests.get(url,headers=headers).text
    sel = Selector(text=res_text)
    name = sel.xpath("//div[@class='lt_main clearfix']/p/text()").extract()[2].strip()
    # 此部分还需要扩展


# 程序的执行入口
if __name__ == '__main__':
    # 导入线程池
    from concurrent.futures import ThreadPoolExecutor
    # 创建线程池对象，最多协程数量10个
    executor = ThreadPoolExecutor(max_wokers=10)
    last_urls = get_last_list()
    for url in last_urls:
        # 执行多任务
        executor.submit(parse_list,url)
