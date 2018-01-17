import json
from urllib.parse import urlencode
from hashlib import md5
from multiprocessing import Pool
import os
import pymongo
from config import *
import re
from bs4 import BeautifulSoup
from requests.exceptions import RequestException
import requests
from json.decoder import JSONDecodeError
client = pymongo.MongoClient(MONGO_URL,connect=False)
db = client[MONGO_DB]


def get_page_index(offset,keyword):
    data = {
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': '20',
        'cur_tab': 3
    }   #复制js的请求参数
    url='https://www.toutiao.com/search_content/?'+ urlencode(data) #对data进行编码，把字典对象转为url的请求参数
    try:
        response = requests.get(url)
        if response.status_code==200: #判断返回状态码
            return response.text #返回网页的文本
        return None
    except RequestException:
        print('请求索引页错误')
        return None

def parse_page_index(html, JSONDecodError=None):
    try:
        data = json.loads(html) #将字符串转换为json对象
        if data and 'data' in data.keys(): #data.keys返回json所有的键名字
            for item in data.get('data'):
                yield item.get('article_url')#拿到详情页的url
    except JSONDecodError:
        pass
def get_page_detail(url):
    try:
        response = requests.get(url)
        if response.status_code==200:
            return response.text
        return None
    except RequestException:
        print('请求详情页错误')
        return None

def parse_page_detail(html, url):
    soup = BeautifulSoup(html, 'lxml')
    result = soup.select('title') #解析js中的title
    title = result[0].get_text() if result else ''
    images_pattern = re.compile('gallery: JSON.parse\("(.*)"\)', re.S) #提取图片的地 址
    result = re.search(images_pattern, html)
    if result:
        data = json.loads(result.group(1).replace('\\', ''))
        if data and 'sub_images' in data.keys():
            sub_images = data.get('sub_images')
            images = [item.get('url') for item in sub_images]
            for image in images:download_image(image)
            return {
                'title': title,
                'url': url,
                'images': images
            }

def save_to_mongo(result):
    if db[MONGO_TABLE].insert(result):
        print('存储成功',result)
        return True
    else:
        print('shibai')
def download_image(url):
    print('正在下载',url)
    try:
        response = requests.get(url)
        if response.status_code==200:
            svae_image(response.content)
        return None
    except RequestException:
        print('请求图片错误')
        return None

def svae_image(content):
    file_path = '{0}/{1}.{2}'.format(os.getcwd(),md5(content).hexdigest(),'jpg')
    if not os.path.exists(file_path):
        with open(file_path,'wb')as f:
            f.write(content)
            f.close()

def main(offset):
    html=get_page_index(offset,KEYWORD)
    for url in parse_page_index(html):
        html = get_page_detail(url)
        if html:
            result = parse_page_detail(html,url)
            if result:save_to_mongo(result)



if __name__ == '__main__':
    group = [x*20 for x in range(GROUP_START,GROUP_END * 1)]
    pool=Pool()
    pool.map(main,group)