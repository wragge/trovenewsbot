trovenewsbot
============

See me in action at [@TroveNewsBot](http://twitter.com/trovenewsbot).

Built using the [Trove API](http://trove.nla.gov.au/general/api).

### Basic bot interactions:

* Include the word 'hello' in a message to @TroveNewsBot to receive a greeting and a random newspaper article.
* Any other message will be treated as a query and will be sent off to the Trove API to look for matching results in the newspaper database.
* To receive any old random newspaper article from amongst the 100 million odd available, just tweet TroveNewsBot the hashtag '#luckydip' and nothing else.

### Modifying your bot query:

By default, the TroveNewsBot tweets the first (ie most relevant) matching result back to you. To change this you can:

* Include the hashtag '#luckydip' to receive a random article from the matching results.
* Include the hashtag '#earliest' to receive the earliest matching article.
* Include the hashtag '#latest' to receive the latest matching article.

By default, the search terms you supply are sent directly to the Trove API without any modification. To change this you can:

* Include the hashtag '#any' to search for articles that match *any* of your search terms. This is the same as adding an 'OR' between your terms.
* Include a year to limit your search to that year.

### Automatic botness:

* At 9am, 3pm and 9pm (AEST), TroveNewsBot tweets a random article that has been updated or added in the previous 24 hours.

Released under CC0 licence.
