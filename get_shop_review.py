# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     get_shop_review
   Description :
   Author :       机器灵砍菜刀
   date：          2018/4/1
-------------------------------------------------
"""
##################################################################
# 次程序的作用是根据主程序中获取的url列表信息，依次提取店铺的详细信息
##################################################################
import requests
import pandas as pd
from lxml import etree
import re
import chardet
import json

simulateBrowserData = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.8',
    'Connection': 'keep-alive',
    'Host': 'sz.nuomi.com',
    'Referer': 'https://sz.nuomi.com/326',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.91 Safari/537.36'
}
simulateIeBrowserData = {
    'Accept': 'text/html,application/xhtml+xml,image/jxr,*/*',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-Hans-CN,zh-Hans;q=0.5',
    'Connection': 'keep-alive',
    'Host': 'sz.nuomi.com',
    'User - Agent': 'Mozilla / 5.0(Windows NT 10.0;Win64;x64) AppleWebKit / 537.36(KHTML, likeGecko) Chrome / 58.0.3029.110Safari / 537.36Edge / 16.16299'
}
# 根据请求url返回数据
def getInfoFromUrl(url):
    try:
        response = requests.get(url, headers=simulateIeBrowserData, timeout=2)
        if response.status_code == 200:
            if response.text:
                # 因为requests这里返回的编码是ISO-8859-1，而非utf-8,所以修改编码方式
                response.encoding = 'utf-8'
                return response.text
            else:
                print('url信息返回为空')
                return getInfoFromUrl(url)
        if response.status_code == 403:
            print('服务器拒绝访问url')
            return getInfoFromUrl(url)
    except Exception as e:
        print('url获取网络连接出错', e)
        return getInfoFromUrl(url)
# 根据店铺返回html，获取概述信息
def getSumInfo(html):
    shop_config_pattern = re.compile('config = (.*?)panorama', re.S)
    # 获取店铺经纬度时，一种情况是含有全景的页面，另外一种无全景
    if re.search(shop_config_pattern, str(html)):
        shop_config = json.dumps(
            re.search(shop_config_pattern, str(html)).group(1).replace('\n', '').replace(' ', '').replace("'", ''),
            ensure_ascii=False)
        shop_config = eval(str(shop_config))
        shop_config_dict = {}
        for item in shop_config.split(','):
            if len(item.split(':', 1)) == 2:
                key = item.split(':', 1)[0]
                value = item.split(':', 1)[1]
                shop_config_dict[key] = value
        lng = shop_config_dict.get('position').split(':')[1]
        lat = shop_config_dict.get('lat').replace('}', '')
    else:
        lat_pattern = re.compile('var lat = (.*?);', re.S)
        lng_pattern = re.compile('var lon = (.*?);', re.S)
        lat = re.search(lat_pattern, str(html)).group(1).replace("'", '')
        lng = re.search(lng_pattern, str(html)).group(1).replace("'", '')
    html = etree.HTML(str(html))
    shopName = html.xpath('//*[@class="shop-box"]/h2/text()')[0].replace('\n', '')
    shopScore = html.xpath('//*[@class="shop-info"]/span[2]/text()')[0]
    if int(html.xpath('//*[@class="shop-info"]/span[3]/a/text()')[0].replace('人评价）', '').replace('（', '')) > 0:
        commentPersonNum = html.xpath('//*[@class="shop-info"]/span[3]/a/text()')[0].replace('人评价）', '').replace('（', '')
        goodCommentNum = html.xpath('//*[@class="level-detail"]/div[1]/span[3]/text()')[0].replace('条', '')
        middleCommentNum = html.xpath('//*[@class="level-detail"]/div[2]/span[3]/text()')[0].replace('条', '')
        badCommentNum = html.xpath('//*[@class="level-detail"]/div[3]/span[3]/text()')[0].replace('条', '')
        allCommentNum = int(goodCommentNum) + int(middleCommentNum) + int(badCommentNum)
    else:
        commentPersonNum = 0
        goodCommentNum = 0
        middleCommentNum = 0
        badCommentNum = 0
        allCommentNum = 0
    if html.xpath('//*[@class="shop-info"]/span[4]/strong/text()'):
        avgPrice = html.xpath('//*[@class="shop-info"]/span[4]/strong/text()')[0].replace('¥', '')
    else:
        avgPrice = 0
    address = html.xpath('//*[@class="shop-list"]/li[1]/p/span[1]/text()')[0]
    phone = html.xpath('//*[@class="shop-list"]/li[2]/p/text()')[0]
    if html.xpath('//*[@class="shop-list"]/li[3]/p/text()'):
        businessHours = html.xpath('//*[@class="shop-list"]/li[3]/p/text()')[0]
    else:
        businessHours = None
    shop_summarize_info = pd.DataFrame({'shopName': [shopName], 'lng': [lng], 'lat': [lat], 'shopScore': [shopScore], 'commentPersonNum': [commentPersonNum],
                                        'avgPrice': [avgPrice], 'address': [address], 'phone': [phone], 'businessHours': [businessHours],
                                        'goodCommentNum': [goodCommentNum], 'middleCommentNum': [middleCommentNum], 'badCommentNum': [badCommentNum],
                                        'allCommentNum': [allCommentNum]})
    shop_summarize_info.to_csv('%sS.csv' % shopId, index=False)
# 获取店铺一共有多少评论页
def getCommentpageNum(comJson):
    try:
        data = json.loads(comJson)
        totalpage = data.get('totalPage')
        if data.get('data').get('pageNum'):
            pageNum = data.get('data').get('pageNum')
        else:
            pageNum = 0
        return pageNum
    except Exception as e:
        print(e)
# 解析每一页店铺评论页Json，获得每页评论信息
def parseCommentJson(commentPageJson):
    try:
        data = json.loads(commentPageJson)
        pageData = pd.DataFrame()
        if 'data' in data.keys():
            if 'list' in data.get('data'):
                for eachCommentInfo in data.get('data').get('list'):
                    nickname = eachCommentInfo.get('nickname')
                    level = eachCommentInfo.get('level')
                    score = eachCommentInfo.get('score')
                    uid = eachCommentInfo.get('uid')
                    create_time = eachCommentInfo.get('create_time')
                    update_time = eachCommentInfo.get('update_time')
                    content = eachCommentInfo.get('content')
                    pageData = pageData.append(
                        pd.DataFrame({'nickname': [nickname], 'userLevel': [level], 'score': [score],
                                      'uid': [uid], 'create_time': [create_time], 'update_time': [update_time],
                                      'content': [content]}))
        return pageData
    except Exception as e:
        print(e)
if __name__ =='__main__':
    url_data = pd.read_csv('shopUrlData.csv', encoding='gbk')
    urls = list(url_data.shop_url)
    shopCount = 0
    complete_shop = 0
    for url in urls:
        complete_shop += 1
        shopId = url.split('shop/')[1]
        if complete_shop > 0:
            print(url)
            html = getInfoFromUrl(url=url)
            getSumInfo(html=html)
            firstComentUrl ='http://www.nuomi.com/pcindex/main/comment?page={0}&merchantId={1}'.format(1, shopId)
            commentJson = getInfoFromUrl(firstComentUrl)
            pageNum = getCommentpageNum(comJson=commentJson)
            # 注意：糯米网上显示的评论数其实非真实的评论数，真实评论数会少于它给定的数量（他的评论数是包含了商家回复数）
            print('编号为{0}的店铺一共有{1}页评论信息'.format(shopId, pageNum))
            shopData = pd.DataFrame()
            if pageNum > 0:
                for i in range(1, pageNum + 1):
                    print('正在抓取第{0}个店铺的第{1}页评论信息......'.format(shopCount + 1, i))
                    commentUrl = 'http://www.nuomi.com/pcindex/main/comment?page={0}&merchantId={1}'.format(i, shopId)
                    commentPageJson = getInfoFromUrl(commentUrl)
                    onePageData = parseCommentJson(commentPageJson=commentPageJson)
                    shopData = shopData.append(onePageData)
                shopData.to_csv('./{0}.csv'.format(shopId), index=False)
                shopCount += 1
                print('已成功爬取%d个店铺信息' % shopCount)
            else:
                shopCount += 1
                print('已成功爬取%d个店铺信息' % shopCount)
