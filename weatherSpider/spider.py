import json
import requests
from requests.exceptions import RequestException
from  lxml import etree

def get_one_page(url):
    try:
        headers = {
            "Accept":"image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Host": "www.pm25.in",
            "Referer": "http://www.pm25.in/assets/application-32570e67636e03a26f6d5c2816025ddb.css",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36"

        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        return None


def parse_one_page(html):
   response = etree.HTML(html)
   content_list = response.xpath('//*[@id="detail-data"]/tbody/tr')
   for site in content_list:
       item = {}
       # 监测点
       item["Mon_point"] = site.xpath('./td[1]/text()')[0]
       # 空气质量
       item["AQI"] = site.xpath('./td[2]/text()')[0]
       # 空气质量指数类别
       AQI_category = site.xpath('./td[3]/text()')
       if len(AQI_category) > 0:
           item["AQI_category"] = AQI_category[0]
       else:
           item["AQI_category"] = "NULL"
       # 首要污染物
       item["pri_pollutant"] = site.xpath('./td[4]/text()')[0]
       # PM2.5细颗粒物
       item["PM2.5"] = site.xpath('./td[5]/text()')[0]
       # PM10可吸入颗粒物
       item["PM10"] = site.xpath('./td[6]/text()')[0]
       # CO一氧化碳
       item["CO"] = site.xpath('./td[7]/text()')[0]
       # NO2二氧化氮
       item["NO2"] = site.xpath('./td[8]/text()')[0]
       # O3臭氧1小时平均
       item["O3_an_hour"] = site.xpath('./td[9]/text()')[0]
       # O3臭氧8小时平均
       item["O3_eight_hour"] = site.xpath('./td[10]/text()')[0]
       # SO2二氧化硫
       item["SO2"] = site.xpath('./td[11]/text()')[0]
       yield item

def write_to_file(content):
    print("正在存储数据......")
    print(content)
    with open('result.txt', 'a', encoding='utf-8') as f:
        f.write(json.dumps(content, ensure_ascii=False) + '\n')


def main():
    print("爬虫启动......")
    url = 'http://www.pm25.in/chongqing'
    html = get_one_page(url)
    for item in parse_one_page(html):
        write_to_file(item)

if __name__ == '__main__':
    main()
