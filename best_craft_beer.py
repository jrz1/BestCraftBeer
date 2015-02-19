#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib
import urllib2
import httplib
# import logging
import operator
import os
import sys
from bs4 import BeautifulSoup

def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except httplib.IncompleteRead, e:
            return e.partial
    return inner

httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)

def logiter(counter=False):
    def wrapper2(func):
        def wrapper(self, *args, **kwargs):
            print "Process started..."
            func(self, counter, *args, **kwargs)
            print "Finished!"
        return wrapper
    return wrapper2


class GetInfo(object):

    def __init__(self, fname):
        self.total_items = {}
        self.file_name   = self.__build_file_name(fname, ".csv")
        self.SRC_URL     = 'http://www.beeryard.com/beer/detail.cfm?id='
        self.DEST_URL    = 'http://www.bing.com/search?q=advocate%20'
        self.SEARCH_URL  = 'beeradvocate.com/beer/profile/'

        # Prepare request headers
        self.hdr = {
            'User-Agent'      : 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
            'Accept'          : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Charset'  : 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
            'Accept-Encoding' : 'none',
            'Accept-Language' : 'en-US,en;q=0.8',
            'Connection'      : 'keep-alive'
        }

    def __build_file_name(self, name, extension):
        PATH = os.path.dirname(os.path.abspath(__file__)) + "/"
        return PATH + name + extension

    def __create_new_file(self, FILE_NAME):
        
        # If file exists, truncate it and start over. Otherwise, create it.
        try:
            with open(FILE_NAME, "w+"): pass
        except IOError:
            open(FILE_NAME, "w+")

        # Open file in append mode and write row headers
        with open(FILE_NAME, "a") as f:
            f.write("Beer Name, Avg Rating,\n")

    def __write_to_file(self, FILE_NAME, dictionary):
        with open(FILE_NAME, "a") as f:
            for name,rating in dictionary:
                f.write(",".join([name, str(rating), '\n']))

    def __get_http_response(self, url, url_param=None):
        req = urllib2.Request("{u}{up}".format(u=url, up=url_param if url_param else ''), headers=self.hdr)
        try:
            response = urllib2.urlopen(req, timeout=10)
        except httplib.IncompleteRead as e:
            # logging.warn("Partial read")
            response = e.partial
        except urllib2.HTTPError:
            # logging.warn("No response")
            response = None
        except urllib2.URLError:
            # logging.warn("There was a URL error")
            response = None

        return response

    def __get_item_name(self, source):
        item_name_original = BeautifulSoup(source).find('span', {'class': 'pgHeaderSm'}).text

        # This is to see if the page is empty,
        # becasue on empty pages, the HTML of the span is simply: ' ()'
        # Three chars: a space, and then two parens
        if item_name_original == " ()":
            item_name_original = None, None
        else:
            item_name_original = item_name_original.replace(u'’', u"'").encode('ascii', 'ignore')
            item_name_safe = urllib.quote(item_name_original, '')  # URL safe
        return item_name_original, item_name_safe

    def __get_score(self, ahref):
        rlist = []
        search_result = self.__get_http_response(ahref)
        final_result  = BeautifulSoup(search_result).findAll('span', {'class':'BAscore_big'})
        for rating in final_result:
            try:
                # Need to cast in order to do arithmetic
                rating = int(BeautifulSoup(str(rating)).find('span', {'class':'BAscore_big'}).text)
                if isinstance(rating, int):
                    rlist.append(rating)
            except ValueError:
                pass
        
        return sum(rlist) / float(len(rlist)) if rlist else None  # Compute average value

    def _get_info(self, i):
        source = self.__get_http_response(self.SRC_URL, i)
        if not source:
            # logging.warn("No source")
            return None, None  # We skip this and move to next one

        item_name_original, item_name_safe = self.__get_item_name(source)
        if not item_name_original or not item_name_safe:
            # logging.warn("lacking criteria")
            return None, None # Again, we skip this and move to next one
        
        page = self.__get_http_response(self.DEST_URL, item_name_safe)
        if not page:
            # logging.warn("No page")
            return None, None # And...again, we skip this and move to next one

        soup = BeautifulSoup(page)      
        for a in soup.find_all('a', href=True):
            ahref = a['href']
            if self.SEARCH_URL in ahref:
                score = self.__get_score(ahref)
                if score:
                    return item_name_original, score

        # logging.warn("Failed attempt to get info")
        return None, None

    @logiter(True)
    def start(self, _counter=False, NUMBEERS=4131):
        self.__create_new_file(self.file_name)
        
        for i in xrange(1, NUMBEERS+1):
            if _counter:
                print "{n} of {t};{nl}".format(n=i, t=NUMBEERS, nl='\n' if i%100==0 else '')

            item_name, score = self._get_info(i)
            if item_name and score:
                if _counter:
                    print item_name, score
                self.total_items[item_name] = score
            if _counter:
                print

        results = sorted(self.total_items.iteritems(), key=operator.itemgetter(1), reverse=True)
        
        self.__write_to_file(self.file_name, results)

def main(args):
    NUMBEERS = 4131
    CSV_NAME = "best_beers"
    if len(args) == 2:
        NUMBEERS = int(args[1])
    if len(args) == 3:
        CSV_NAME = args[2]

    GetInfo(CSV_NAME).start(NUMBEERS)

if __name__ == '__main__':
    main(sys.argv)
