from pdb import set_trace as st
from inspect import getmembers as gm

import unittest
import os
import tempfile
import re

from bs4 import BeautifulSoup

from capp import app
from capp import initdb

## debug util functions

def gmn(obj, all=False):
    """ get member names """
    return [n for (n, _) in gm(obj)
            if all or (re.match('^_', n) is None and
                       re.match('^__.*__$', n) is None)]

## util functions

def bs(html_str):
    return BeautifulSoup(html_str, 'html5lib')

## Page objects (http://martinfowler.com/bliki/PageObject.html)

class AssertionMixin(object):

    def assertEqual(self, x, y):
        assert(x == y)

    def assertTrue(self, x):
        assert(x)


class PageObject(AssertionMixin, object):

    def __init__(self, soup, test=None):
        self.soup = soup
        if test:
            self.assertEqual = test.assertEqual
            self.assertTrue = test.assertTrue


    def class_tags(self, class_name=None, classes=None):
        """ get all tags of a certain class """
        if class_name is not None and classes is not None:
            raise TypeError(("class_tags takes one of 'class_tags' "
                             "or 'classes' args"))
        if class_name is not None:
            if type(class_name) != type(''):
                raise ValueError("class_name should be a string")
            return self.soup.find_all(
                lambda t: (t.get('class') and
                           class_name in t.get('class')))
        if classes is not None:
            if type(classes) != type([]):
                raise ValueError("classes should be a list")
            return [tag
                    for class_name in classes
                    for tags in self.class_tags(class_name)
                    for tag in tags]
        raise TypeError(("class_tags takes at least one argument"))

    def class_tag(self, class_name):
        tags = self.class_tags(class_name)
        self.assertEqual(len(tags), 1)
        return tags[0]


class HomePage(PageObject):

    def get_brand(self):
        brand_tag = self.class_tag('navbar-brand')
        return brand_tag.text.strip()


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

    def test_get_home(self):
        self._get_page_soup('/')

    def test_home_struct(self):
        soup = self._get_page_soup('/')
        page = HomePage(soup, self)
        self.assertEqual(page.get_brand(),
                         'Catalog App')


if __name__ == '__main__':
    unittest.main()
