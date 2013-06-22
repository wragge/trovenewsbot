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


LAST_ID = '/home/dhistory/apps/trovenewsbot/src/last_id.txt'
#LAST_ID = 'last_id.txt'
LOCK_FILE = '/home/dhistory/apps/trovenewsbot/src/locked.txt'
#LOCK_FILE = 'locked.txt'
API_QUERY = 'http://api.trove.nla.gov.au/result?q={keywords}&zone=newspaper&l-category=Article&key={key}&encoding=json&n={number}&s={start}&reclevel=full&sortby={sort}'
START_YEAR = 1803
END_YEAR = 1954
PERMALINK = 'http://nla.gov.au/nla.news-article{}'
GREETING = 'Greetings human! Insert keywords. Use #luckydip for randomness.'
LOG_FILE = '/home/dhistory/apps/trovenewsbot/src/errors.txt'
#LOG_FILE = 'errors.txt'


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
        start=0
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


def process_tweet(text, user):
    random = False
    hello = False
    sort = 'relevance'
    trove_url = None
    text = text[14:].replace(u'\u201c', '"').replace(u'\u201d', '"')
    query = text.strip()
    if re.search(r'\bhello\b', query, re.IGNORECASE):
        query = ''
        random = True
        hello = True
    if '#luckydip' in query:
        # Get a random article
        query = query.replace('#luckydip', '').strip()
        random = True
    if '#earliest' in query:
        query = query.replace('#earliest', '').strip()
        sort = 'dateasc'
    if '#latest' in query:
        query = query.replace('#latest', '').strip()
        sort = 'datedesc'
    if '#any' in query:
        query = query.replace('#any', '').strip()
        print "'{}'".format(query)
        query = '({})'.format(' OR '.join(query.split()))
    query = extract_date(query)
    start = 0
    while trove_url is None:
        article = get_article(query, random, start, sort)
        if not article:
            if query:
                # Search failed
                message = "@{user} ERROR! No article matching '{text}'.".format(user=user, text=text)
            else:
                # Something's wrong, let's just give up.
                message = None
            break
        else:
            # Filter out 'coming soon' articles
            try:
                trove_url = article['troveUrl']
            except (KeyError, TypeError):
                pass
            start += 1
            time.sleep(1)
    if article:
        url = PERMALINK.format(article['id'])
        fdate = utilities.format_iso_date(article['date'])
        title = article['heading']
        if hello:
            chars = 118 - (len(user) + len(fdate) + len(GREETING) + 8)
            title = title[:chars]
            message = "@{user} {greeting} {date}: '{title}' {url}".format(user=user, greeting=GREETING, date=fdate, title=title.encode('utf-8'), url=url)
        else:
            chars = 118 - (len(user) + len(fdate) + 7)
            title = title[:chars]
            message = "@{user} {date}: '{title}' {url}".format(user=user, greeting=GREETING, date=fdate, title=title.encode('utf-8'), url=url)
    return message


def get_article(text, random=False, start=0, sort=''):
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
            logging.exception('Got exception on retrieving tweets')
        #message = process_tweet('"mount stromlo" light pollution', 'wragge')
        #print message
        for tweet in results:
            if tweet.in_reply_to_screen_name == 'TroveNewsBot':
                #print tweet.text
                try:
                    message = process_tweet(tweet.text, tweet.user.screen_name)
                except:
                    logging.exception('Got exception on process_tweet')
                if message:
                    try:
                        #print message
                        api.PostUpdate(message, in_reply_to_status_id=tweet.id)
                    except:
                        logging.exception('Got exception on sending tweet')
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
