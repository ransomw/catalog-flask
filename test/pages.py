""" Page objects (http://martinfowler.com/bliki/PageObject.html) """

import re

def arr_elem(assert_equal, arr):
    assert_equal(len(arr), 1)
    return arr[0]

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

    def _arr_elem(self, arr):
        return arr_elem(self.assertEqual, arr)

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
        return self._arr_elem(self.class_tags(class_name))

    def tags_with_text(self, tag_re, text_re):
        return self.soup.find_all(
            lambda t: (re.match(tag_re, t.name) is not None and
                       re.match(text_re, t.text.strip()) is not None))

    def tag_with_text(self, tag_re, text_re):
        return self._arr_elem(self.tags_with_text(tag_re, text_re))


class NavPage(PageObject):
    """ page containing the nav bar """

    @property
    def brand(self):
        brand_tag = self.class_tag('navbar-brand')
        return brand_tag.text.strip()

    @property
    def login_url(self):
        return self.tag_with_text(r'^a$', r'^Login$')

class CatsPage(PageObject):

    def _cats_div(self):
        elem = self.tag_with_text(r'^h.', r'^Categories$').parent
        self.assertEqual(elem.name, 'div')
        return elem

    @property
    def cats(self):
        return [{'name': tag.text.strip(),
                 'url': tag.attrs['href']}
                for tag in self._cats_div().find_all('a')]


class HomePage(NavPage, CatsPage, PageObject):

    def _items_div(self):
        elem = self.tag_with_text(r'^h.', r'^Latest Items$').parent
        self.assertEqual(elem.name, 'div')
        return elem

    @property
    def items(self):
        return [{'title': tag.a.text.strip(),
                 'cat': tag.span.text.strip().strip('()'),
                 'url': tag.a.attrs['href']}
                for tag in self._items_div().find_all('li')]


class ItemsPage(NavPage, CatsPage, PageObject):

    def _items_h(self):
        return self.tag_with_text(r'^h.$', r'.*Items')

    def _items_div(self):
        elem = self._items_h().parent
        self.assertEqual(elem.name, 'div')
        return elem

    @property
    def items(self):
        return [{'title': tag.a.text.strip(),
                 'url': tag.a.attrs['href']}
                for tag in self._items_div().find_all('li')]

    @property
    def item_list_header_text(self):
        return self._items_h().text
