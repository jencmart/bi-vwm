#!/usr/bin/env python
# coding: utf-8

# In[60]:


import requests
import re
from bs4 import BeautifulSoup
import bs4
import string
import re
from pprint import pprint
import csv
import time
import pandas as pd
from functools import partial
import math
from time import sleep
import random
import os

cnt_query=0


# ### Some shitty parsing helpers funcs

# In[44]:


def remove_leading_tailing_spaces_commas(s):
    s1 = re.sub(r"^\s+|\s+$", "", s)
    s2 = re.sub(r"^\,+|\,+$", "", s1)
    s3 = re.sub(r"^\s+|\s+$", "", s2)
    return s3


def extract_first_number_or_zero(dirty):
    dirty = re.sub(r"\D+", " ", dirty)
    lst = [int(s) for s in dirty.split() if s.isdigit()]
    if len(lst) > 0:
        return lst[0]
    else:
        return 0

    
def extract_last_number_or_zero(dirty):
    dirty = re.sub(r"\D+", " ", dirty)
    lst = [int(s) for s in dirty.split() if s.isdigit()]
    if len(lst) > 0:
        return lst[-1]
    else:
        return 0
    
    
def parse_price(buy): #  SAFE
    if buy is None:
        return 0, 0, 0
    # -- p -- class: price
    price = buy.find('p', attrs={'class':'price'})
    if price is None:
        return 0, 0, 0
    
    item_price_from = price.find('span', attrs={'class':'priceFrom'})
    if item_price_from is None:
        return 0, 0, 0
    
    item_price_from = extract_first_number_or_zero(item_price_from.getText())
    price_to = price.find('span', attrs={'class':'priceTo'})
    if price_to is None:
        item_price_to = item_price_from
        item_shop_count = 1
    else:
        item_price_to = price_to.getText()
        item_price_to = extract_first_number_or_zero(item_price_to)
        # -- p -- shop count (only if multiple prices)
        item_shop_count = buy.find('p', attrs={'class':'count'})
        if item_shop_count is None:
            return item_price_from, item_price_to, 1
        item_shop_count = item_shop_count.find('a')
        if item_shop_count is None:
            return item_price_from, item_price_to, 1
        item_shop_count = extract_first_number_or_zero(item_shop_count.getText())

    return item_price_from, item_price_to, item_shop_count


def parse_reviews(desc): # SAFE
     # -- p -- class: rw
    reviews = desc.find('p', attrs={'class':'rw'})
    if reviews is None :
        return 0, 0
    
    item_rating = reviews.find('span', attrs={'class':'rating'})
    if item_rating is None:
        return 0, 0
    item_rating = item_rating.find('span', attrs={'class':'hidden'})
    if item_rating is None:
        return 0, 0
    item_rating = extract_first_number_or_zero(item_rating.getText())
    
    item_reviews_cnt = reviews.find('span', attrs={'class':'review-count'})
    if item_reviews_cnt is None :
        item_reviews_cnt = 0
    else:
        item_reviews_cnt = item_reviews_cnt.find('a')
        if item_reviews_cnt is None:
            return 0, 0
        item_reviews_cnt = item_reviews_cnt.getText() 
        item_reviews_cnt = extract_first_number_or_zero(item_reviews_cnt)                
        
    return item_rating, item_reviews_cnt
        
def parse_description(desc): # SAFE
    # -- div -- class: desc
    desc_text = desc.find('p', attrs={'class':'desc'})
    if desc_text is None:
        return ''
    
    item_description = ''
    for itm in desc_text:
        if  type(itm) is bs4.element.NavigableString:
            item_description = itm.string
    return item_description


def parse_id_and_name(desc): # SAFE
    # -- div -- class: product-container
    item_container = desc.find('div', attrs={'class':'product-container'})
    if item_container is None:
        return '', ''
    item_id = item_container.get('id')
    item_name = item_container.find('h2').find('a').getText()
    
    return item_id, item_name
  
    
languages = ['anglické', 'chorvatské', 'dánské', 'francouzské', 'holandské', 'italské', 'japonské', 'latinské', 'maďarské', 'německé', 'polské', 'portugalské', 'ruské', 'slovenské', 'turecké', 'vietnamské', 'Česky', 'české', 'čínské', 'řecké', 'španělské']
genres = ['beletrie', 'cestopisy', 'dobrodružství, humor', 'duchovno', 'dětské', 'esoterika', 'historická beletrie', 'horory', 'kuchařky', 'křížovky', 'naučná', 'náboženství', 'osobní rozvoj', 'poezie', 'populárně naučná', 'pro ženy', 'Psychologický román', 'román', 'romány pro ženy', 'sci-fi a fantasy', 'slovníky', 'zdraví a životní styl', 'životopisy']
# last always language
# between numbers - author
# genres -- matchneme
# problem: no numbers -- co je author a co je nakaladatelstvi
# ['Grada', 'dětské', 'Antonín Šplíchal, české']
# dobrodružství, Panteon, 2019, Jonas Jonasson, 400, české

def parse_hard_shit(s):
    gen = ''
    lng = ''
    prod = ''
    auth = ''
    s1 = re.sub(r'<p class="params">', "", s)
    s1 = re.sub(r'<abbr title="Počet stran">[0-9]+</abbr>,', 'XXX', s1) # pages
    s1 = re.sub(r'<abbr title="Rok vydání">[0-9]+</abbr>,', 'XXX', s1) # year
    result = [x.strip() for x in s1.split(',')]

    for l in languages:
        if l+'</p>' == result[-1]:
            lng = l
            s1 = re.sub(l+'</p>', 'XXX', s1)
            break

    result = [x.strip() for x in s1.split(',')]
    for g in genres:
        for r in result:
            if g == r:
                gen = g
                s1 = re.sub(g+',', 'XXX', s1)
                break

    # chybi - autor && nakladatelstvi

    s1 = re.sub(r'XXX', '', s1) # year
    s1 = remove_leading_tailing_spaces_commas(s1)
    result = [x.strip() for x in s1.split(',')]
    result

    if len(result) == 1:
        auth = result[0]

    if len(result) == 2:
        prod = result[0]
        auth = result[1]

    if len(result) > 2:
        for r in reversed(result):
            if (' ' in r):
                auth = r
                break
          
    if auth != '':
        result.remove(auth)
        if prod == '':
            if len(result) > 0:
                for r in result:
                    if r.isalpha():
                        prod = r
                        break
    
    prod = remove_leading_tailing_spaces_commas(prod)
    auth = remove_leading_tailing_spaces_commas(auth)
    return prod, gen, auth, lng

def parse_params(desc): # SAFE
    # -- p -- class: params
    publisher = ''
    genre = ''
    author = ''
    lang = ''
    year = 0
    pages_cnt = 0
    
    params = desc.find('p', attrs={'class':'params'})
    if params is None:
        return year, pages_cnt, publisher, genre, author, lang, ""
    
    unknown = []
    for param in params:
        if  type(param) is bs4.element.NavigableString:
            unknown.append(remove_leading_tailing_spaces_commas(param.string))
        elif param.get('title') == 'Rok vydání':
            year = extract_first_number_or_zero(param.getText())
        elif param.get('title') == 'Počet stran':
            pages_cnt = extract_first_number_or_zero(param.getText())
    params = str(params)
    publisher, genre, author, lang = parse_hard_shit(params)
    return year, pages_cnt, publisher, genre, author, lang, unknown


# ### Parse product

# In[45]:


# ID, name, rating, reviews_cnt, year, pages_cnt, publisher, genre, author, lang, description, price_from, price_to, unparsed
def parse_product(product):
   
    # [DESCRIPTION DIV]
    desc = product.find('div', attrs={'class':'desc'})  # ok always
    ID, name = parse_id_and_name(desc)  # SAFE
    rating, reviews_cnt = parse_reviews(desc)  # SAFE
    year, pages_cnt, publisher, genre, author, lang, unparsed = parse_params(desc)  # SAFE
    description = parse_description(desc)  # SAFE
    
    # [BUY DIV]
    buy = product.find('div', attrs={'class':'buy'})
    price_from, price_to, shop_count = parse_price(buy)  # SAFE
    
    return [ID, name, rating, reviews_cnt, year, pages_cnt, publisher, genre, author, lang, description, price_from, price_to, unparsed]


# # Main crawl-loop

# ### Count results helper

# In[61]:


def cnt_results_crawl(soup):  # SAFE
    cnt_items = soup.find('div',  attrs={'class':'sort-bottom'})
   
    if cnt_items != None:
        cnt_items = cnt_items.find('div',  attrs={'class':'count'})
        if cnt_items != None:
            cnt = extract_last_number_or_zero(cnt_items.getText())
        else:
            cnt = 0
    else:
        cnt = 0
    return cnt

def get_number_of_results_from_url(url):
    url = url 
    t = time.time()
    cnt_shit = 1
    global cnt_query
    while True:
        try:
            cnt_query+=1
            print(cnt_query)
            r = requests.get(url,timeout=10)
            if len(r.url.split(';'))!=len(url.split(';')):
                print('not found: '+url)
                return 0
            soup = BeautifulSoup(r.text)
            break
        except Exception as e:  # This is the correct syntax
            print ('some shit happend')
            sleep(60*cnt_shit)
            cnt_shit +=1
            print(cnt_shit)

    t = time.time() - t
    print('crawled cnt pages; time [{0:.2f}s]'.format(t))
    cnt_res = cnt_results_crawl(soup)
    print('found: '+str(cnt_res)+' results at: '+url)
    return cnt_res


# ## Scrapping loop - all pages based on URL

# In[47]:


def format_filename(s):
#     value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
#     value = unicode(re.sub('[^\w\s-]', '', value).strip().lower())
#     value = unicode(re.sub('[-\s]+', '-', value))
#     return value
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    filename = ''.join(c for c in s if c in valid_chars)
    filename = filename.replace(' ','_') # I don't like spaces in filenames.
    return filename


def create_filename(url):
    url = url.replace('https://knihy.heureka.cz/f:', '')
    list_url = url.split(';')
    final_list = []
    for part in list_url:
        part = part.replace(':', ',')
        part_list = part.split(',')
        part_list.sort()
        final_list += part_list


    final_list = list(set(final_list))
    final_list.sort()
    for i in final_list:
        i = format_filename(i)
        
    search = '' + '-'.join(final_list) + '.csv'
    return search


# In[62]:


def scrap_all_pages_from_url_save_to_cvs(url, filename = None, BenchMark=False,from_page = 1, max_pages = 10, timeout = 0.5):
        
    if filename is not None:
        print('using custom filename')
    else:
        filename = create_filename(url)
        
    cnt_scrapped = 0
    

    existing_file = False
    if not BenchMark:
        
        # check for existing scrap
        filename = 'scrapped/' + filename
        try:
            fh = open(filename, 'r')
            df_tmp = pd.read_csv(filename)
            cnt_scrapped = df_tmp.shape[0]
            existing_file = True
        except FileNotFoundError:
            pass
    
    t_total = time.time()
    
    # scrap number of results and pages
    cnt_results = get_number_of_results_from_url(url)
    cnt_pages = math.ceil(cnt_results/30.0)
    
    
    # if max pages <= 0 ... then crawl all pages
    to_page = cnt_pages
    if max_pages < cnt_pages:
        to_page = max_pages
        
    # force full scrape if BenchMark
    if BenchMark:
        cnt_scrapped=0
        
    # allready fully scrapped
    if cnt_scrapped == cnt_results:
        print('allready fully scraped. nothing to do')
        return 0
    
  
    # partially scrapped
    if cnt_scrapped > 0:
        print('allready exisitng filename')
        print('with [{}] results, from [{}] possible. [] remaining'.format(cnt_scrapped, cnt_results,  cnt_results - cnt_scrapped))
        cnt_pages_scrapped = math.floor(cnt_scrapped/30.0)
        from_page = cnt_pages_scrapped + 1
        print('---------------------------------------------------------')
        print('staring to scrap rest [{}] pages; limit [{}] = [{}] products'.format(cnt_pages - cnt_pages_scrapped, max_pages, max_pages*30))
        print('---------------------------------------------------------')
    
    # not scrapped
    else:
        print('---------------------------------------------------------')
        print('staring to scrap [{}] pages; limit [{}] = [{}] products'.format(cnt_pages, max_pages, max_pages*30))
        print('---------------------------------------------------------')

    res = pd.DataFrame(columns=['db_id', 'name', 'rating', 'reviews_cnt', 'year', 'pages_cnt', 'publisher', 'genre', 'author', 'lang', 'description', 'price_from', 'price_to', 'unparsed'])
    
    ###########################################################
    # just for nicely padded print :-)
    padding = 1
    tmp = to_page
    while tmp >= 10:
        tmp /= 10
        padding +=1
    padd = 'scrapping [{0:0'+str(padding)+'d}'
    ##########################################################
    global cnt_query
    # go through all pages
    for i in range(from_page,to_page+1):        
        # page
        url_paged = url + '/?f=' + str(i) # # ...../?f=1
        
        print(padd.format(i), end = '')
        print('/{}]'.format(to_page), end='')
        # scrap it (+ measure time)
        t1 = time.time()
        
        #################################################### fix all errors :-)
        cnt_shit = 1
        while True:
            try:
                cnt_query+=1
                print(cnt_query)
                r = requests.get(url,timeout=10)
                soup = BeautifulSoup(r.text)
                break
            except Exception as e:  # This is the correct syntax
                print ('some shit happend')
                sleep(60*cnt_shit)
                cnt_shit +=1
                print(cnt_shit)
        ####################################################
        
        
        
        
        t1 = time.time() - t1
        print('[{0:.2f}s]'.format(t1), end = '')
        
        # parse up to 30 product from page
        products = soup.find_all('div', attrs={'class':'p'}) # ok safe now 
        for product in products:
            parsed_product = parse_product(product)
            res = res.append(pd.Series(parsed_product, index=res.columns), ignore_index=True) 
       
        print('[OK] sleeping [{}s]'.format(timeout))
        sleep(timeout)
        
        
        # save often..
        if i > 10 and  i % 10:
            if existing_file:
                with open(filename, 'a') as f:
                    res.to_csv(f,  index=False, header=False)
                    res = pd.DataFrame(columns=['db_id', 'name', 'rating', 'reviews_cnt', 'year', 'pages_cnt', 'publisher', 'genre', 'author', 'lang', 'description', 'price_from', 'price_to', 'unparsed'])
            else:
                res.to_csv(filename, index=False)
                existing_file = True
                res = pd.DataFrame(columns=['db_id', 'name', 'rating', 'reviews_cnt', 'year', 'pages_cnt', 'publisher', 'genre', 'author', 'lang', 'description', 'price_from', 'price_to', 'unparsed'])
    
    # final save
    if filename!="BenchMark":
        if existing_file:
            with open(filename, 'a') as f:
                res.to_csv(f,  index=False, header=False)
        else:
            res.to_csv(filename, index=False)

    t_total = time.time() - t_total
    print('---------------------------------------------------------')
    print('scraped [{}] pages = [{}] products; '.format(to_page, len(res)), end = '')
    print('total time [{0:.2f}s]'.format(t_total))
    print('---------------------------------------------------------')
    print (cnt_results)
    return cnt_results


# ### URL's

# ### Dictionary generator

# In[49]:


def generate_publisher_list(crawled_csv, min_cnt_occurences = 4, shuffle = True):
    languages = ['anglické', 'chorvatské', 'dánské', 'francouzské', 'holandské', 'italské', 'japonské', 'latinské', 'maďarské', 'německé', 'polské', 'portugalské', 'ruské', 'slovenské', 'turecké', 'vietnamské', 'Česky', 'české', 'čínské', 'řecké', 'španělské']
    genres = ['beletrie', 'cestopisy', 'dobrodružství, humor', 'duchovno', 'dětské', 'esoterika', 'historická beletrie', 'horory', 'kuchařky', 'křížovky', 'naučná', 'náboženství', 'osobní rozvoj', 'poezie', 'populárně naučná', 'pro ženy', 'Psychologický román', 'román', 'romány pro ženy', 'sci-fi a fantasy', 'slovníky', 'zdraví a životní styl', 'životopisy']
    df = pd.read_csv(crawled_csv)
    # misto jazyku None
    df.loc[df["publisher"].isin(languages), "publisher"] = None
    # misto genre None
    df.loc[df["publisher"].isin(genres), "publisher"] = None
    # dropni vsechny None
    df = df.dropna(subset=['publisher'])
    # count and sort
    df = df.groupby('publisher').publisher.count().reset_index(name='count').sort_values(['count'], ascending=False)
    # only with higher num of occurences
    r = df.loc[df['count'] >= min_cnt_occurences]
    # create python list
    list_of_publishers = r.publisher.tolist()
    # replace some shit
    for i in range(len(list_of_publishers)):
        list_of_publishers[i] = list_of_publishers[i].lower() # to lower
        list_of_publishers[i] = list_of_publishers[i].replace(" ", "%20") # encode spaces
        list_of_publishers[i] = list_of_publishers[i].replace("#", "") # some shitty names
        list_of_publishers[i] = list_of_publishers[i].replace("&amp;", "&")
        list_of_publishers[i] = list_of_publishers[i].replace("/", "%7C")
        list_of_publishers[i] = list_of_publishers[i].replace('á', 'a')         .replace('č', 'c')         .replace('ď', 'd')         .replace('é', 'e')         .replace('ě', 'e')         .replace('í', 'i')         .replace('ň', 'n')         .replace('ó', 'o')         .replace('ř', 'r')         .replace('š', 's')         .replace('ť', 't')         .replace('ú', 'u')         .replace('ů', 'u')         .replace('ý', 'y')         .replace('ý', 'y')         .replace('ž', 'z')         .replace('ľ', 'l')
        list_of_publishers[i] = '_' + list_of_publishers[i]  # and add underscore at the beggin
    # eventually randum shuffle
    if shuffle:
        random.shuffle(list_of_publishers)
        
    return list_of_publishers


# ### predefined url

# In[50]:


base_url = 'https://knihy.heureka.cz/f:'

predefined = [ {'pref':'4625', 'suffix' : ['16494','16495','16496','16497','16498']} ,
               {'pref': '4620',  'suffix': ['1900','1905','1907','1911','1920','1925','1928','1930','1931','1934','1940','1946','1947','1948','1949','1950','1951','1952','1953','1954','1955','1956','1957','1958','1959','1960','1961','1962','1963','1964','1965','1966','1967','1968','1969','1970','1971','1972','1973','1974','1975','1976','1977','1978','1979','1980','1981','1982','1983','1984','1985','1986','1987','1988','1989','1990','1991','1992','1993','1994','1995','1996','1997','1998','1999','2000','2001','2002','2003','2004','2005','2006','2007','2008','2009','2010','2011','2012','2013','2014','2015','2016','2017','2018','2019','2020','2025']},
               {'pref' : '4619', 'suffix' : ['22929248','531655','268123','431096','29313706','27688452','259848','259855','26095413','27890885','555182','259836','24319385','174508','26737347','27593856','27596982','27688656','531656','24636535','531658','26152179','259828']},
               {'pref' : '4627' ,'suffix' : ['66288','66300','21366767','69330','21277184','102484','70032','102483','133027','102482','67392','84188','79763','170155','93','21364634','17989634','21366766','133028','67579','102485']}             
             ]


# # logic constructing URL's
# * heureka me zarizla
#     * po 49  crawlech (timeout 0.5s)
#     * po 278 crawlech (timeout 5s)
# * -> chce to vychytat ty timeouty

# In[51]:


def wordHelper(dicts, idx_dict  = 0):
        prefix = dicts[idx_dict]['pref']
        suffixes = dicts[idx_dict]['suffix']
        return suffixes, prefix

def logicHelper(predef, dicts, index, url, maxResults, fileName=None, maxBenchMarkResults=100000000000, benchMark=False,timeout=0.5): # recursive adding indexes up to all used
        if index!=0: # next query
            url=url+';'
        res_count=0   
        # if we're out of predefined, use dict
        if index==len(predef):

            # generate dict
            suffixes, prefix = wordHelper(dicts, 0)

            # go through dict
            for suffix in suffixes:
                # and download whever possible
                pom =get_number_of_results_from_url(url+ prefix +':'+suffix)
                sleep(timeout)
                if pom <=maxResults and pom > 0:

                    res_count+=scrap_all_pages_from_url_save_to_cvs(url+ prefix +':'+suffix,fileName,benchMark,timeout=timeout)


            # finally return. we have no other options ...
            return res_count

        else:
            suffixes=predef[index]['suffix'] # suffixes only from current index
            # random.shuffle(suffixes)
            prefix = predef[index]['pref']

        while len(suffixes)>0 and res_count<maxBenchMarkResults: # till we have some suffiexes
            lo=0
            hi=len(suffixes)-1
            mid=0

            strsuff=""
            while lo<hi:
                mid=(int)((lo+hi+1)/2) 
                if prefix=='4620':
                    strsuff=suffixes[0]+"-"+suffixes[mid]
                else:
                    strsuff=','.join(suffixes[:mid+1])
                if get_number_of_results_from_url(url + prefix + ':' + strsuff )>maxResults:
                    hi=mid-1
                else: # enough
                    lo=mid
                sleep(timeout)

            mid = lo
            if prefix=='4620':
                strsuff=suffixes[0]+"-"+suffixes[mid]
            else:
                strsuff=','.join(suffixes[:mid+1])

            # if too much results
            if mid==0 and len(suffixes)>0:
                if len(suffixes)==1 and get_number_of_results_from_url(url+ prefix +':'+strsuff)<=maxResults:
                    res_count+=scrap_all_pages_from_url_save_to_cvs(url+ prefix +':'+strsuff,fileName,benchMark,timeout=timeout)
                    return res_count

                print( str(mid)+ "   :   "+str(len(suffixes)))
                res_count+=logicHelper(predef, dicts, index+1,url+ prefix +':'+strsuff,maxResults,fileName,maxBenchMarkResults-res_count,benchMark,timeout=timeout) # only first suffix 
                suffixes=suffixes[1:] # and remove it

            else: # enough
                res_count+=scrap_all_pages_from_url_save_to_cvs(url+ prefix +':'+strsuff,fileName,benchMark,timeout=timeout)
                suffixes=suffixes[mid+1:]
        return res_count


# # Benchmark code
# 

# In[52]:


def run_benchmark(size):
    publisher_list = generate_publisher_list('scrapped_old/test.csv', min_cnt_occurences = 5, shuffle = True)
    dicts = [    {'pref':'4621', 'suffix' : publisher_list}, # publisher
                 {'pref' : '4624' ,'suffix' : []},  # author
                 {'pref' : '19863' ,'suffix' : []}, # producer
                 {'pref' : 'q' ,'suffix' : []} # fulltext
            ]
    t=time.time()
    fileBenchMark="BenchMark"
    logicHelper(predefined, dicts, 0 ,base_url,300,fileBenchMark,size,True)
    t=time.time()-t
    print("time: ", t, " seconds")
    return t


# # Full scrape

# In[64]:


def run_scrape():
    # generate some dicts
    publisher_list = generate_publisher_list('scrapped_old/test.csv', min_cnt_occurences = 5, shuffle = True)
    dicts = [    {'pref':'4621', 'suffix' : publisher_list}, # publisher
                 {'pref' : '4624' ,'suffix' : []},  # author
                 {'pref' : '19863' ,'suffix' : []}, # producer
                 {'pref' : 'q' ,'suffix' : []} # fulltext
            ]


    logicHelper(predefined, dicts,0,base_url , 300, timeout=0)


# ## Afterprocessing

# In[54]:


def merge():
    files= os.listdir("scrapped")
    data =pd.read_csv("scrapped/"+files[0])

    # now the rest:    
    for num in range(1,len(files)):
        data = pd.concat([data,pd.read_csv("scrapped/"+files[num])])
    print(len(data))
    data.to_csv("merged.csv")


# In[68]:


def get_scrapped_count():
    data=pd.read_csv("deduplicated.csv")
    return len(data)


# In[66]:


def dedupliaction():
    data =pd.read_csv("merged.csv")
    data=data.drop(columns = 'Unnamed: 0')
    df1=data.drop_duplicates(subset='db_id',keep='first', inplace=False)
    df1.to_csv("deduplicated.csv")


# # Start the code

# In[67]:


# run_benchmark(1000)
# run_scrape()
# dedupliaction()

