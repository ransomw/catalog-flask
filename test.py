from pdb import set_trace as st

import unittest
import os
import tempfile

from bs4 import BeautifulSoup

from capp import app
from capp import initdb

def BS(html_str):
    return BeautifulSoup(html_str, 'html5lib')

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


class NoLoginTests(BaseTestCase):

    def test_get_home(self):
        resp = self.c.get('/')
        soup = BS(resp.data)
        brand_tags = soup.find_all(
            lambda t: (t.get('class') and
                       'navbar-brand' in t.get('class')))
        self.assertTrue(len(brand_tags) == 1)
        self.assertEqual(brand_tags[0].text.strip(),
                         'Catalog App')


if __name__ == '__main__':
    unittest.main()
