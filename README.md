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

### Opinionator Mode:

If you tweet a url to TroveNewsBot you enter *Opinionator* mode. In this mode, TroveNewsBot examines the page at the supplied url and builds a query based on it's contents. The result is a commentary of sorts drawn from from TroveNewsBot's reservoir of 100 million historic newspaper articles.

#### Titles

By default, TroveNewsBot assembles its query by looking for a number of elements on the page:

* The first set of <h1></h1> tags
* A meta tag with a name including the string 'title'
* Whatever's in the <title></title> tag

TroveNewsBot takes the text of whichever of these is found first, removes stopwords, slices off the first ten words, sends them off to Trove, and tweets the result.

#### Keywords

If you add the hashtag '#keywords' to a tweet containing a url, TroveNewsBot uses the [AlchemyAPI](http://www.alchemyapi.com/) to extract the ten top-ranked key words or phrases from the complete text of the page. These are then sent to Trove as before. This should probably (maybe) increase the relevance of TroveNewsBot's response.

### Automatic botness:

* At 9am, 3pm and 9pm (AEST), TroveNewsBot tweets a random article that has been updated or added in the previous 24 hours.

Released under CC0 licence.
