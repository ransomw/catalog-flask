from pdb import set_trace as st
from inspect import getmembers as gm

import unittest
import os
import tempfile
import re

from bs4 import BeautifulSoup

from capp import app
from capp import initdb

from test.pages import arr_elem
from test.pages import HomePage
from test.pages import ItemsPage

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

    def get_home_page(self):
        return HomePage(self._get_page_soup('/'), self)


class NavMixin(BaseTestCase):

    def _test_nav(self, page):
        self.assertEqual(page.brand,
                         'Catalog App')
        page.login_url


class CatsMixin(BaseTestCase):

    def _test_cats(self, page):
        self.assertEqual(set(self.CATS),
                         set([cat['name'] for cat in page.cats]))


class NoLoginTests(NavMixin, CatsMixin, BaseTestCase):

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

    def test_home(self):
        page = self.get_home_page()
        self._test_nav(page)
        self._test_cats(page)
        items = page.items
        self.assertEqual(set([i['title'] for i in self.ITEMS]),
                         set([i['title'] for i in items]))
        for curr_item in items:
            expected_item = arr_elem(
                self.assertEqual,
                [i for i in self.ITEMS
                 if i['title'] == curr_item['title']])
            self.assertEqual(expected_item['cat'], curr_item['cat'])

    def test_items(self):
        home_page = self.get_home_page()
        for cat in home_page.cats:
            items_page = ItemsPage(
                self._get_page_soup(cat['url']), self)
            self._test_nav(items_page)
            self._test_cats(items_page)
            expected_item_titles = [
                item['title']
                for item in self.ITEMS
                if item['cat'] == cat['name']]
            self.assertEqual(
                set(expected_item_titles),
                set([item['title'] for item in
                     items_page.items])
                ,msg="items page for category "+cat['name']
            )
            self.assertEqual(
                items_page.item_list_header_text,
                ''.join([cat['name'], " Items (",
                         str(len(expected_item_titles)), " items)"]))


        # page = ItemsPage(HomePage(
        #     self.get_home_page().login_url)


if __name__ == '__main__':
    unittest.main()
