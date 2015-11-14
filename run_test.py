from pdb import set_trace as st
from inspect import getmembers as gm

import unittest
import os
import tempfile
import re
import random
from urlparse import urlparse
from StringIO import StringIO

from bs4 import BeautifulSoup

from capp import app
from capp import initdb

from test.pages import arr_elem
from test.pages import HomePage
from test.pages import ItemsPage
from test.pages import ItemPage
from test.pages import LoginPage
from test.pages import CreatePage
from test.pages import EditPage
from test.pages import DeletePage

## debug util functions

def gmn(obj, all=False):
    """ get member names """
    return [n for (n, _) in gm(obj)
            if all or (re.match('^_', n) is None and
                       re.match('^__.*__$', n) is None)]

## util functions

def bs(html_str):
    return BeautifulSoup(html_str, 'html5lib')

########################
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

    def test_item_pages(self):
        item_pages = [ItemPage(self._get_page_soup(i['url']), self)
                      for i in self.get_home_page().items]
        self.assertEqual(len(item_pages), len(self.ITEMS))
        for page in item_pages:
            expected_description = arr_elem(
                self.assertEqual,
                [i['description'] for i in self.ITEMS
                 if i['title'] == page.title])
            self.assertEqual(page.description, expected_description)
            self.assertFalse(page.has_edit_link())
            self.assertFalse(page.has_delete_link())

# todo: test g+ and github logins
#       consider defining all functionality in terms of mixins,
#       one for each type of login and one for the tests,
#       then defining three tests classes by combining
#       each login mixin with the test mixin
#    ...even though even this won't cover the case where a name and email
#    are manually added to an account between some of the tests


class LoginMixin(BaseTestCase):

    EMAIL = 'a@a.org'
    PASS = 'password'
    NAME = 'alice'

    def sign_up(self, url):
        page = LoginPage(self._get_page_soup(url), self)
        form_dict = page.form_dict
        form_dict.update({
            'sign-up': '',
            'password': self.PASS,
            'email': self.EMAIL,
            'password-confirm': self.PASS,
            # todo: omitting the name param is a good way to make the
            #       database crash
            'name': self.NAME,
        })
        resp = self.c.post(url,
                           data=form_dict.post_dict,
                           follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

    def login(self, url):
        page = LoginPage(self._get_page_soup(url), self)
        form_dict = page.form_dict
        form_dict.update({
            'sign-in': '',
            'password': self.PASS,
            'email': self.EMAIL,
        })
        resp = self.c.post(url,
                           data=form_dict.post_dict,
                           follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

    def sign_up_login(self, url):
        self.sign_up(url)
        self.login(url)

    def logout(self, nav_page):
        resp = self.c.get(nav_page.logout_url, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)


class LoginTests(LoginMixin, NavMixin, CatsMixin, BaseTestCase):

    def test_login(self):
        self.sign_up_login(self.get_home_page().login_url)
        self.logout(self.get_home_page())
        self.get_home_page().login_url

# todo: tests via database api

class CrudTests(LoginMixin, NavMixin, CatsMixin, BaseTestCase):

    ITEM = {
        'title': "Ball",
        'description': "World Cup 2014 edition",
        'cat': "Soccer",
    }

    # todo: avoid duplicate item titles
    #       changing 'title' to 'Stick' leads to weird errors
    ITEM_UPDATE = {
        'title': "Russian hockey stick",
        'description': "infested with termites (a-la The Simspons)",
        'cat': "Hockey"
    }


    def setUp(self):
        super(CrudTests, self).setUp()
        # set picture here, or else
        # ValueError: I/O operation on closed file
        # occurs when _create() is run more than once
        # not posting an empty picture string leads to 400 error
        # change StringIO to ByteIO for python3 (?)
        # the second elem in the tuple is the filename
        self.ITEM['picture'] = (StringIO(''), '')
        self.ITEM_UPDATE['picture'] = (StringIO(''), '')

    def _update_item_form_dict(self, form_dict, update_vals):
        # todo: edit FormDict to make the following cleaner
        #       ideally, a single .update() would suffice
        form_dict['category'].selected = update_vals['cat']
        item_dict = dict(update_vals)
        item_dict.pop('cat')
        form_dict.update(item_dict)

    def _create(self):
        self.sign_up_login(self.get_home_page().login_url)
        create_url = self.get_home_page().create_url
        page = CreatePage(self._get_page_soup(create_url), self)
        form_dict = page.form_dict
        self._update_item_form_dict(form_dict, self.ITEM)
        resp = self.c.post(create_url,
                           data=form_dict.post_dict,
                           follow_redirects=True,
                           content_type=form_dict.content_type)
        self.assertEqual(resp.status_code, 200)

    def test_create(self):
        self._create()

    def _get_item_page(self, item_title):
        item_url = arr_elem(
            self.assertEqual,
            [i['url'] for i in self.get_home_page().items
             if i['title'] == item_title])
        return ItemPage(self._get_page_soup(item_url), self)

    def _test_read(self, expected_vals):
        item_page = self._get_item_page(expected_vals['title'])
        # todo: check item category
        #       while removing duplicate code from NoLoginTest
        self.assertEqual(item_page.title, expected_vals['title'])
        self.assertEqual(item_page.description,
                         expected_vals['description'])

    def test_read(self):
        self._create()
        self._test_read(self.ITEM)

    def test_update(self):
        self._create()
        item_page = self._get_item_page(self.ITEM['title'])
        edit_url = item_page.edit_url
        edit_page = EditPage(
            self._get_page_soup(edit_url), self)
        form_dict = edit_page.form_dict
        self._update_item_form_dict(form_dict, self.ITEM_UPDATE)
        resp = self.c.post(edit_url,
                           data=form_dict.post_dict,
                           follow_redirects=True,
                           content_type=form_dict.content_type)
        self.assertEqual(resp.status_code, 200)
        self._test_read(self.ITEM_UPDATE)

    def test_delete(self):
        self._create()
        self.assertEqual(len([i for i in self.get_home_page().items
                              if i['title'] == self.ITEM['title']]), 1)
        item_page = self._get_item_page(self.ITEM['title'])
        delete_url = item_page.delete_url
        delete_page = DeletePage(
            self._get_page_soup(delete_url), self)
        form_dict = delete_page.form_dict
        resp = self.c.post(delete_url,
                           data=delete_page.form_dict.post_dict,
                           follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([i for i in self.get_home_page().items
                          if i['title'] == self.ITEM['title']], [])


if __name__ == '__main__':
    unittest.main()
