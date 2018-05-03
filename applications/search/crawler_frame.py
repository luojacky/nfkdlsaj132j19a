import logging
from datamodel.search.Luoj9Joseo1_datamodel import Luoj9Joseo1Link, OneLuoj9Joseo1UnProcessedLink
from spacetime.client.IApplication import IApplication
from spacetime.client.declarations import Producer, GetterSetter, Getter
from lxml import html,etree
import re, os
from time import time
from uuid import uuid4

from urlparse import urlparse, parse_qs, urljoin
from uuid import uuid4
from bs4 import BeautifulSoup
from tldextract import tldextract

logger = logging.getLogger(__name__)
LOG_HEADER = "[CRAWLER]"

@Producer(Luoj9Joseo1Link)
@GetterSetter(OneLuoj9Joseo1UnProcessedLink)
class CrawlerFrame(IApplication):
    app_id = "Luoj9Joseo1"

    def __init__(self, frame):
        self.app_id = "Luoj9Joseo1"
        self.frame = frame


    def initialize(self):
        self.count = 0
        links = self.frame.get_new(OneLuoj9Joseo1UnProcessedLink)
        if len(links) > 0:
            print "Resuming from the previous state."
            self.download_links(links)
        else:
            l = Luoj9Joseo1Link("http://www.ics.uci.edu/")
            print l.full_url
            self.frame.add(l)

    def update(self):
        unprocessed_links = self.frame.get_new(OneLuoj9Joseo1UnProcessedLink)
        if unprocessed_links:
            self.download_links(unprocessed_links)

    def download_links(self, unprocessed_links):
        for link in unprocessed_links:
            print "Got a link to download:", link.full_url
            downloaded = link.download()
            links = extract_next_links(downloaded)
            for l in links:
                if is_valid(l):
                    self.frame.add(Luoj9Joseo1Link(l))

    def shutdown(self):
        print (
            "Time time spent this session: ",
            time() - self.starttime, " seconds.")

subdomain_count = {}
links = {}

def extract_next_links(rawDataObj):
    outputLinks = []
    '''
    rawDataObj is an object of type UrlResponse declared at L20-30
    datamodel/search/server_datamodel.py
    the return of this function should be a list of urls in their absolute form
    Validation of link via is_valid function is done later (see line 42).
    It is not required to remove duplicates that have already been downloaded. 
    The frontier takes care of that.
    
    Suggested library: lxml
    '''
    url = rawDataObj.url
    if(rawDataObj.is_redirected):
        url = rawDataObj.final_url
    subdomain = tldextract.extract(url).subdomain
    if subdomain != "":
        if subdomain not in subdomain_count:
            subdomain_count[subdomain] = 1
        else:
            subdomain_count[subdomain] += 1
    if not (400 <= rawDataObj.http_code <= 599):
        soup = BeautifulSoup(rawDataObj.content, 'lxml')
        links[url] = 0
        try:
            for link in soup.find_all('a'):
                href = urljoin(url,link.get('href')).encode("utf-8")
                outputLinks.append(href)
                if href != url and is_valid(href):
                    links[url] += 1
        except:
            pass
    with open("analytics.txt", 'w') as outfile:
        outfile.write("Subdomains and their number of urls processed:\n")
        for subdomain in sorted(subdomain_count.items(), key=lambda x:x[1], reverse=True):
            outfile.write("    " + subdomain[0] + ": " +str(subdomain[1]) + "\n")
        sorted_links = sorted(links.items(), key=lambda x:x[1], reverse=True)
        outfile.write("The link with the most out links:\n")
        outfile.write("    " + sorted_links[0][0] + ": " + str(sorted_links[0][1]))
    return outputLinks

def is_valid(url):
    '''
    Function returns True or False based on whether the url has to be
    downloaded or not.
    Robot rules and duplication rules are checked separately.
    This is a great place to filter out crawler traps.
    '''
    parsed = urlparse(url)
    if parsed.scheme not in set(["http", "https"]):
        return False
    check_repeating = r"^.*?(/.+?/).*?\1.*$|^.*?/(.+?/)\2.*$"   # first group checks anywhere for repeats, second group checks directly repeating words
    check_calendar = r"^.*calendar.*$"
    check_length = r"^.*/[^/]{100,}$"
    check_equal = r"^.*?=.*?=.*?=.*?$"
    check_page = r"^.*?page.*?page.*?$"
    try:
        return ".ics.uci.edu" in parsed.hostname \
            and not re.match(".*\.(css|js|bmp|gif|jpe?g|ico" + "|png|tiff?|mid|mp2|mp3|mp4"\
            + "|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf" \
            + "|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso|epub|dll|cnf|tgz|sha1" \
            + "|thmx|mso|arff|rtf|jar|csv"\
            + "|rm|smil|wmv|swf|wma|zip|rar|gz|pdf)$", parsed.path.lower()) \
            and not re.match(check_repeating, url) \
            and not re.match(check_calendar, url) \
            and not re.match(check_length, url) \
            and not re.match(check_equal, url) \
            and not re.match(check_page, url)

    except TypeError:
        print ("TypeError for ", parsed)
        return False

