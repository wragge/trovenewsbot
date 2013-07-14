import urllib
import httplib2
import json
import random
import twitter
import credentials
import utilities
import re
import argparse
import datetime
import time
import logging
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
import feedparser
import nltk

try:
    from file_locations_prod import *
except ImportError:
    pass
try:
    from file_locations_dev import *
except ImportError:
    pass

API_QUERY = 'http://api.trove.nla.gov.au/result?q={keywords}&zone=newspaper&l-category=Article&key={key}&encoding=json&n={number}&s={start}&reclevel=full&sortby={sort}'
START_YEAR = 1803
END_YEAR = 1954
PERMALINK = 'http://nla.gov.au/nla.news-article{}'
GREETING = 'Greetings human! Insert keywords. Use #luckydip for randomness.'
ALCHEMY_KEYWORD_QUERY = 'http://access.alchemyapi.com/calls/url/URLGetRankedKeywords?url={url}&apikey={key}&maxRetrieve=10&outputMode=json&keywordExtractMode=strict'
ABC_RSS = 'http://www.abc.net.au/news/feed/51120/rss.xml'
GEONAMES = 'http://api.geonames.org/findNearbyJSON?lat={lat}&lng={lon}&username={user}'

logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG,)


def lock():
    with open(LOCK_FILE, 'w') as lock_file:
        lock_file.write('1')
    return True


def unlock():
    with open(LOCK_FILE, 'w') as lock_file:
        lock_file.write('0')
    return True


def is_unlocked():
    with open(LOCK_FILE, 'r') as lock_file:
        if lock_file.read().strip() == '0':
            return True
        else:
            return False


def get_api_result(query):
    h = httplib2.Http()
    resp, content = h.request(query)
    try:
        json_data = json.loads(content)
    except ValueError:
        json_data = None
    return json_data


def get_start(text):
    query = API_QUERY.format(
        keywords=urllib.quote_plus(text),
        key=credentials.api_key,
        number=0,
        start=0,
        sort='relevance'
    )
    json_data = get_api_result(query)
    total = int(json_data['response']['zone'][0]['records']['total'])
    print total
    return random.randint(0, total)


def get_random_year():
    year = random.randint(START_YEAR, END_YEAR)
    return 'date:[{0} TO {0}]'.format(year)


def extract_date(text):
    if re.search(r'\b\d{4}\b', text):
        year = re.search(r'(\b\d{4}\b)', text).group(1)
        text = re.sub(r'\b\d{4}\b', 'date:[{0} TO {0}]'.format(year), text)
    return text


def extract_params(query):
    if '#any' in query:
        query = query.replace('#any', '')
        query = '({})'.format(' OR '.join(query.split()))


def extract_title(url):
    h = httplib2.Http()
    query = None
    try:
        resp, content = h.request(url)
        soup = BeautifulSoup(content)
        if soup.find('h1'):
            query = soup.find('h1').string.strip()
        elif soup.find('meta', name=re.compile('title')):
            query = soup.find('meta', name=re.compile('title'))['content'].strip()
        elif soup.find('title'):
            query = soup.find('title').string.strip()
    except httplib2.ServerNotFoundError:
        return None
    return query


def get_alchemy_result(query_url):
    h = httplib2.Http()
    url = ALCHEMY_KEYWORD_QUERY.format(
        key=credentials.alchemy_api,
        url=urllib.quote_plus(query_url)
    )
    resp, content = h.request(url)
    results = json.loads(content)
    print results
    return results


def extract_url_keywords(tweet, text):
    query = None
    keywords = []
    try:
        url = tweet.urls[0].url
    except (IndexError, NameError):
        return None
    else:
        if '#keywords' in text:
            # Use Alchemy
            results = get_alchemy_result(url)
            for keyword in results['keywords']:
                if len(keyword['text'].split()) > 1:
                    keywords.append('"{}"'.format(keyword['text']))
                else:
                    keywords.append(keyword['text'])
        else:
            # Get page title
            title = extract_title(url)
            if title:
                title = title.replace(u'\u2018', '').replace(u'\u2019', '').replace(u'\u201c', '').replace(u'\u201d', '')
                words = nltk.word_tokenize(title)
                keywords = [word.lower() for word in words if word.lower() not in stopwords.words('english') and word.isalnum()]
                keywords = keywords[:10]
    query = '({})'.format(' OR '.join(keywords))
    print query
    return query


def get_geonames_result(coords):
    h = httplib2.Http()
    url = GEONAMES.format(
        user=credentials.geonames,
        lat=coords[1],
        lon=coords[0]
    )
    resp, content = h.request(url)
    results = json.loads(content)
    return results


def extract_location(tweet, text):
    try:
        coords = tweet.coordinates['coordinates']
        print coords
    except (IndexError, NameError, AttributeError, TypeError):
        return ''
    else:
        results = get_geonames_result(coords)
        try:
            placename = results['geonames'][0]['name'].strip()
            print placename
        except KeyError:
            return ''
    return placename


def process_tweet(tweet):
    query = None
    random = False
    hello = False
    placename = ''
    sort = 'relevance'
    trove_url = None
    text = tweet.text.strip()
    user = tweet.user.screen_name
    text = text[14:].replace(u'\u201c', '"').replace(u'\u201d', '"')
    if re.search(r'\bhello\b', text, re.IGNORECASE):
        query = ''
        random = True
        hello = True
    else:
        if '#luckydip' in text:
            # Get a random article
            text = text.replace('#luckydip', '').strip()
            random = True
        if '#earliest' in text:
            text = text.replace('#earliest', '').strip()
            sort = 'dateasc'
        if '#latest' in text:
            text = text.replace('#latest', '').strip()
            sort = 'datedesc'
        if '#here' in text:
            text = text.replace('#here', '').strip()
            placename = extract_location(tweet, text)
            text = '{}{}'.format('{} '.format(text) if text else '', placename)
        if '#any' in text:
            text = text.replace('#any', '').strip()
            #print "'{}'".format(query)
            query = '({})'.format(' OR '.join(query.split()))
        else:
            query = extract_url_keywords(tweet, text)
            if not query:
                query = extract_date(text)
    start = 0
    while trove_url is None:
        article = get_article(query, random, start, sort)
        if not article:
            if query:
                # Search failed
                message = "@{user} ERROR! No article matching '{text}'.".format(user=user, text=text)
            else:
                # Something's wrong, let's just give up.
                message = "@{user} ERROR! Something went wrong. [:-(] {date}".format(user=user, date=datetime.datetime.now())
            break
        else:
            # Filter out 'coming soon' articles
            try:
                trove_url = article['troveUrl']
            except (KeyError, TypeError):
                pass
            # Don't keep looking forever
            if start < 60:
                start += 1
                time.sleep(1)
            else:
                message = "@{user} ERROR! Something went wrong. [:-(] {date}".format(user=user, date=datetime.datetime.now())
                article = None
                break
    if article:
        url = PERMALINK.format(article['id'])
        fdate = utilities.format_iso_date(article['date'])
        title = article['heading']
        if hello:
            chars = 118 - (len(user) + len(fdate) + len(GREETING) + 8)
            title = title[:chars]
            message = "@{user} {greeting} {date}: '{title}' {url}".format(user=user, greeting=GREETING, date=fdate, title=title.encode('utf-8'), url=url)
        else:
            chars = 118 - (len(user) + len(fdate) + len(placename) + 7)
            title = title[:chars]
            message = "@{user} {place}{date}: '{title}' {url}".format(user=user, greeting=GREETING, date=fdate, title=title.encode('utf-8'), url=url, place='{}'.format('{}, '.format(placename) if placename else ''))
    return message


def get_article(text, random=False, start=0, sort='relevance'):
    if random:
        if not text:
            text = get_random_year()
        start = get_start(text)
    query = API_QUERY.format(
        keywords=urllib.quote_plus(text),
        key=credentials.api_key,
        number=1,
        start=start,
        sort=sort
    )
    print query
    json_data = get_api_result(query)
    try:
        article = json_data['response']['zone'][0]['records']['article'][0]
    except (KeyError, IndexError, TypeError):
        return None
    else:
        return article


def tweet_reply(api):
    if is_unlocked():
        lock()
        message = None
        with open(LAST_ID, 'r') as last_id_file:
            last_id = int(last_id_file.read().strip())
        #print api.VerifyCredentials()
        try:
            results = api.GetMentions(since_id=last_id)
        except:
            logging.exception('{}: Got exception on retrieving tweets'.format(datetime.datetime.now()))
        #message = process_tweet('"mount stromlo" light pollution', 'wragge')
        #print message
        for tweet in results:
            if tweet.in_reply_to_screen_name == 'TroveNewsBot':
                #print tweet.text
                try:
                    message = process_tweet(tweet)
                except:
                    logging.exception('{}: Got exception on process_tweet'.format(datetime.datetime.now()))
                    message = None
                if message:
                    try:
                        print message
                        api.PostUpdate(message, in_reply_to_status_id=tweet.id)
                    except:
                        logging.exception('{}: Got exception on sending tweet'.format(datetime.datetime.now()))
                time.sleep(20)
        if results:
            with open(LAST_ID, 'w') as last_id_file:
                last_id_file.write(str(max([x.id for x in results])))
        unlock()


def tweet_random(api):
    trove_url = None
    now = datetime.datetime.utcnow()
    then = now - datetime.timedelta(hours=24)
    then = then.strftime('%Y-%m-%dT00:00:00Z')
    text = 'lastupdated:[{} TO *]'.format(then)
    while not trove_url:
        article = get_article(text, True)
        try:
            trove_url = article['troveUrl']
        except (KeyError, TypeError):
            pass
        time.sleep(1)
    if int(article['correctionCount']) > 0:
        alert = 'Updated!'
    else:
        alert = 'New!'
    url = PERMALINK.format(article['id'])
    fdate = utilities.format_iso_date(article['date'])
    chars = 118 - (len(alert) + len(fdate) + 6)
    title = article['heading'][:chars]
    message = "{alert} {date}: '{title}' {url}".format(alert=alert, date=fdate, title=title.encode('utf-8'), url=url)
    print message
    api.PostUpdate(message)


def tweet_opinion(api):
    trove_url = None
    keywords = []
    article = None
    start = 0
    news = feedparser.parse(ABC_RSS)
    latest_url = news.entries[0].link
    with open(LAST_URL, 'r') as last_url_file:
        last_url = last_url_file.read().strip()
    if latest_url != last_url:
        try:
            results = get_alchemy_result(latest_url)
        except:
            logging.exception('{}: Got exception on alchemyapi'.format(datetime.datetime.now()))
        else:
            if results['keywords']:
                for keyword in results['keywords']:
                    if len(keyword['text'].split()) > 1:
                        keywords.append('"{}"'.format(keyword['text']))
                    else:
                        keywords.append(keyword['text'])
                query = '({})'.format(' OR '.join(keywords))
                while not trove_url:
                    try:
                        article = get_article(query, start=start)
                    except:
                        logging.exception('{}: Got exception on get_article'.format(datetime.datetime.now()))
                    else:
                        try:
                            trove_url = article['troveUrl']
                        except (KeyError, TypeError):
                            pass
                        # Don't keep looking forever
                        if start < 60:
                            start += 1
                            time.sleep(1)
                        else:
                            article = None
                            break
                if article:
                    url = PERMALINK.format(article['id'])
                    fdate = utilities.format_iso_date(article['date'])
                    chars = 79 - len(fdate)
                    title = article['heading'][:chars]
                    message = "{date}: '{title}' {url} // re ABC: {news}".format(news=latest_url, date=fdate, title=title.encode('utf-8'), url=url)
                    with open(LAST_URL, 'w') as last_url_file:
                        last_url_file.write(latest_url)
                    try:
                        print message
                        api.PostUpdate(message)
                    except:
                        logging.exception('{}: Got exception on sending tweet'.format(datetime.datetime.now()))
            else:
                logging.error('{}: Alchemy API said: {}'.format(datetime.datetime.now(), results['statusInfo']))


def tweet_dpla(api):
    trove_url = None
    keywords = []
    article = None
    start = 0
    try:
        tweets = api.GetUserTimeline(screen_name='DPLAbot', count=1)
        #print tweets[0]
    except:
        logging.exception('{}: Got exception on retrieving tweet'.format(datetime.datetime.now()))
    try:
        latest_url = tweets[0].urls[0].url
    except (IndexError, NameError):
        return None
    else:
        with open(LAST_DPLA, 'r') as last_dpla_file:
            last_url = last_dpla_file.read().strip()
        if latest_url != last_url:
            try:
                results = get_alchemy_result(latest_url)
            except:
                logging.exception('{}: Got exception on alchemyapi'.format(datetime.datetime.now()))
            else:
                if results['keywords']:
                    for keyword in results['keywords']:
                        if len(keyword['text'].split()) > 1:
                            keywords.append('"{}"'.format(keyword['text']))
                        else:
                            keywords.append(keyword['text'])
                    query = '({})'.format(' OR '.join(keywords))
                    while not trove_url:
                        try:
                            article = get_article(query, start=start)
                        except:
                            logging.exception('{}: Got exception on get_article'.format(datetime.datetime.now()))
                        else:
                            try:
                                trove_url = article['troveUrl']
                            except (KeyError, TypeError):
                                pass
                            # Don't keep looking forever
                            if start < 60:
                                start += 1
                                time.sleep(1)
                            else:
                                article = None
                                break
                    if article:
                        url = PERMALINK.format(article['id'])
                        fdate = utilities.format_iso_date(article['date'])
                        chars = 78 - len(fdate)
                        title = article['heading'][:chars]
                        message = "{date}: '{title}' {url} // re DPLA: {dpla}".format(dpla=latest_url, date=fdate, title=title.encode('utf-8'), url=url)
                        with open(LAST_DPLA, 'w') as last_dpla_file:
                            last_dpla_file.write(latest_url)
                        try:
                            print message
                            api.PostUpdate(message)
                        except:
                            logging.exception('{}: Got exception on sending tweet'.format(datetime.datetime.now()))
                else:
                    logging.error('{}: Alchemy API said: {}'.format(datetime.datetime.now(), results['statusInfo']))



if __name__ == '__main__':
    api = twitter.Api(
        consumer_key=credentials.consumer_key,
        consumer_secret=credentials.consumer_secret,
        access_token_key=credentials.access_token_key,
        access_token_secret=credentials.access_token_secret
    )
    parser = argparse.ArgumentParser()
    parser.add_argument('task')
    args = parser.parse_args()
    if args.task == 'reply':
        tweet_reply(api)
    elif args.task == 'random':
        tweet_random(api)
    elif args.task == 'opinion':
        tweet_opinion(api)
    elif args.task == 'dpla':
        tweet_dpla(api)
