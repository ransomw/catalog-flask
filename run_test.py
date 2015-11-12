from pdb import set_trace as st
from inspect import getmembers as gm

import unittest
import os
import tempfile
import re

from bs4 import BeautifulSoup

from capp import app
from capp import initdb

from test.pages import HomePage
from test.pages import arr_elem

## debug util functions

def gmn(obj, all=False):
    """ get member names """
    return [n for (n, _) in gm(obj)
            if all or (re.match('^_', n) is None and
                       re.match('^__.*__$', n) is None)]

## util functions

def bs(html_str):
    return BeautifulSoup(html_str, 'html5lib')

## test cases

class BaseTestCase(unittest.TestCase):

    def setUp(self):
        # os file handle (as by os.open), absolute pathname
        self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
        # disables error catching during request handling
        app.config['TESTING'] = True
        self.c = app.test_client()
        with app.app_context():
            initdb()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(app.config['DATABASE'])

    def _get_page_soup(self, url):
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 200)
        return bs(resp.data)


class NoLoginTests(BaseTestCase):

    CATS = [
        "Soccer",
        "Basketball",
        "Baseball",
        "Frisbee",
        "Snowboarding",
        "Rock Climbing",
        "Foosball",
        "Skating",
        "Hockey"
    ]

    ITEMS = [
        {'title': "Stick",
         'description': "A hockey stick",
         'cat': "Hockey"},
        {'title': "Goggles",
         'description': "Keep the snow out of your eyes",
         'cat': "Snowboarding"},
        {'title': "Snowboard",
         'description': "Type-A vintage",
         'cat': "Snowboarding"},
        {'title': "Two shinguards",
         'description': "Prevent injuries resulting from kicks to the shin",
         'cat': "Soccer"},
        {'title': "Shinguards",
         'description': "Prevent injuries resulting from kicks to the shin",
         'cat': "Soccer"},
        {'title': "Frisbee",
         'description': "A flying disc",
         'cat': "Frisbee"},
        {'title': "Bat",
         'description': "Louisville slugger",
         'cat': "Baseball"},
        {'title': "Jersey",
         'description': "World Cup 2014 commemorative jersy",
         'cat': "Soccer"},
        {'title': "Soccer Cleats",
         'description': "Nike cleats",
         'cat': "Soccer"},
    ]

    def test_get_home(self):
        self._get_page_soup('/')

    def test_home(self):
        soup = self._get_page_soup('/')
        page = HomePage(soup, self)
        self.assertEqual(page.brand(),
                         'Catalog App')
        self.assertEqual(set(self.CATS),
                         set([cat['name'] for cat in page.get_cats()]))
        items = page.get_items()
        self.assertEqual(set([i['title'] for i in self.ITEMS]),
                         set([i['title'] for i in items]))
        for curr_item in items:
            expected_item = arr_elem(
                self.assertEqual,
                [i for i in self.ITEMS
                 if i['title'] == curr_item['title']])
            self.assertEqual(expected_item['cat'], curr_item['cat'])
        page.get_login_url()



if __name__ == '__main__':
    unittest.main()
