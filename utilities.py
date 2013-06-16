import re
import calendar
import datetime
import time


def retry(ExceptionToCheck, tries=4, delay=3, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
        excpetions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """
    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            try_one_last_time = True
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                    try_one_last_time = False
                    break
                except ExceptionToCheck, e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    if logger:
                        logger.warning(msg)
                    else:
                        print msg
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            if try_one_last_time:
                return f(*args, **kwargs)
            return
        return f_retry  # true decorator
    return deco_retry


def parse_date(date_string):
    date_obj = None
    day = False
    month = False
    date_formats = [('%d %B %Y', True, True),
                    ('%d %b %Y', True, True),
                    ('%d %b. %Y', True, True),
                    ('%B %Y', False, True),
                    ('%b %Y', False, True),
                    ('%Y', False, False),
                    ]
    for date_format in date_formats:
        try:
            date_obj = datetime.datetime.strptime(date_string, date_format[0])
        except ValueError:
            pass
        else:
            day = date_format[1]
            month = date_format[2]
            break
    return {'date': date_obj, 'day': day, 'month': month}


def process_date_string(date_string):
    '''
    Takes a date range in a string and returns date objects,
    and booleans indicating if values for month and day exist.
    '''
    dates = date_string.split('-')
    if dates:
        start_date = parse_date(dates[0].strip())
        try:
            end_date = parse_date(dates[1].strip())
        except IndexError:
            end_date = None
    return {'date_str': date_string, 'start_date': start_date, 'end_date': end_date}


def convert_date_to_iso(date_dict):
    '''
    Simple ISO date formatting.
    Not dependent on strftime and its year limits.
    '''
    date_obj = date_dict['date']
    if date_obj:
        if date_dict['day']:
            iso_date = '{0.year}-{0.month:02d}-{0.day:02d}'.format(date_obj)
        elif date_dict['month']:
            iso_date = '{0.year}-{0.month:02d}'.format(date_obj)
        else:
            iso_date = '{0.year}'.format(date_obj)
    else:
        iso_date = None
    return iso_date


def format_iso_date(iso_date):
    year, month, day = iso_date.split('-')
    return '{} {} {}'.format(int(day), calendar.month_abbr[int(month)], year)
