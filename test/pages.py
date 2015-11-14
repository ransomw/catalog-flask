""" Page objects (http://martinfowler.com/bliki/PageObject.html) """

from pdb import set_trace as st

import re

## utility functions

def arr_elem(assert_equal, arr):
    assert_equal(len(arr), 1)
    return arr[0]

## beautifulsoup helpers

class SelectDict(dict):

    def __init__(self, bs_select):
        options = bs_select.find_all('option')
        # todo: check if html has selected attr set on some option
        self._selected = options[0].text.strip()
        return super(SelectDict, self).__init__(
            [(t.text.strip(), t.attrs['value'])
             for t in bs_select.find_all('option')])

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, val):
        if val not in self.keys():
            raise ValueError("unknown selection '" + str(val) + "'")
        self._selected = val

    @property
    def selected_val(self):
        return self.get(self.selected)


class FormDict(dict):

    @property
    def form(self):
        return self._form

    def _get_kv_list(self, tag_name):
        kv_list = [(t.attrs['name'], None)
                   for t in self.form.find_all(tag_name)
                   if ('name' in t.attrs.keys() and
                       'value' not in t.attrs.keys())]
        kv_list += [(t.attrs['name'], t.attrs['value'])
                   for t in self.form.find_all(tag_name)
                   if ('name' in t.attrs.keys() and
                       'value' in t.attrs.keys())]
        return kv_list

    def __init__(self, bs_form):
        self._form = bs_form
        self._content_type = bs_form.attrs.get('enctype', None)
        kv_list = self._get_kv_list('button')
        # todo: special handling for type=file inputs
        #       for these, werkzeug.Client.post(data={'k': isn't a string
        kv_list += self._get_kv_list('input')
        kv_list += [(t.attrs['name'], SelectDict(t))
                    for t in self.form.find_all('select')]
        return super(FormDict, self).__init__(kv_list)

    @property
    def content_type(self):
        return self._content_type

    # todo: FormDict doesn't give desired behavior on setitem
    #     TypeError: argument of type
    #         'builtin_function_or_method' is not iterable
    # on form_dict[key] = val

    # def __setitem__(self, key, value):
    #     if key not in self.keys:
    #         raise ValueError("may not add new fields to form")
    #     return super(FormDict, self).__setitem__(key, value)

    # todo: FormDict should also throw error on update with invalid keys

    @property
    def post_dict(self):
        post_dict = dict(self)
        for key in post_dict.keys():
            if post_dict[key] is None:
                post_dict.pop(key)
            elif type(post_dict[key]) == SelectDict:
                post_dict[key] = post_dict[key].selected_val
        return post_dict

    # todo: add action and url properties to FormDict
    #       edit uses to, e.g., self.c.post(url or form_dict.url)


class AssertionMixin(object):
    """ interface for unittest.TestCase asserts """
    def assertEqual(self, x, y):
        assert(x == y)

    def assertTrue(self, x):
        assert(x)


###################
## page objects

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
        return arr_elem(self.assertEqual, self.class_tags(class_name))

    def tags_with_text(self, tag_re, text_re):
        return self.soup.find_all(
            lambda t: (re.match(tag_re, t.name) is not None and
                       re.match(text_re, t.text.strip()) is not None))

    def tag_with_text(self, tag_re, text_re):
        return arr_elem(self.assertEqual,
                        self.tags_with_text(tag_re, text_re))


class NavPage(PageObject):
    """ mixin for page containing the nav bar """

    @property
    def brand(self):
        brand_tag = self.class_tag('navbar-brand')
        return brand_tag.text.strip()

    @property
    def login_url(self):
        return self.tag_with_text(r'^a$', r'^Login$').attrs['href']

    @property
    def logout_url(self):
        return self.tag_with_text(r'^a$', r'^Logout$').attrs['href']


class CatsPage(PageObject):
    """ mixin for page containing categories list """

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
                for tag in self._items_div().ul.find_all('li')]

    @property
    def create_url(self):
        return self.tag_with_text(r'^a$', r'^Add item$').attrs['href']


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
                for tag in self._items_div().ul.find_all('li')]

    @property
    def item_list_header_text(self):
        return self._items_h().text


class ItemPage(NavPage, PageObject):

    def _get_main_div(self):
        return self.soup.h3.parent

    @property
    def title(self):
        return self._get_main_div().h3.text.strip()

    @property
    def description(self):
        desc_text = self._get_main_div().p.text.strip()
        desc_match = re.match(r'Description: (.*)', desc_text)
        self.assertTrue(desc_match is not None)
        # group(0) is entire string
        return desc_match.group(1)

    @property
    def edit_url(self):
        return self.tag_with_text(r'^a$', r'^Edit$').attrs['href']

    @property
    def delete_url(self):
        return self.tag_with_text(r'^a$', r'^Delete$').attrs['href']

    def has_edit_link(self):
        return len(self.tags_with_text(r'^a$', r'^Edit$')) != 0

    def has_delete_link(self):
        return len(self.tags_with_text(r'^a$', r'^Delete$')) != 0


class LoginPage(PageObject):

    def _get_form(self):
        return self.soup.form

    @property
    def form_dict(self):
        return FormDict(self._get_form())


class CreatePage(NavPage, PageObject):

    @property
    def form_dict(self):
        return FormDict(self.soup.form)


class EditPage(CreatePage):
    pass


class DeletePage(NavPage, PageObject):

    @property
    def form_dict(self):
        return FormDict(self.soup.form)
