# -*- coding: utf-8 -*-
'''
    inflection
    ~~~~~~~~~~~~

    A port of Ruby on Rails' inflector to Python.

    :copyright: (c) 2012-2015 by Janne Vanhala

    :license: MIT, see LICENSE for more details.
'''
import itertools
import re
from locale import getdefaultlocale
from operator import itemgetter
from unicodedata import normalize

__version__ = '0.4.0'


def _ci_re(pattern):
    return '(?i:%s)' % (pattern, )


def _as_re(string):
    string = re.escape(string)
    string = _ci_re(string)
    return r'\b%s\Z' % (string, )


def _transform_group(func, group=0):
    def _match(match):
        s = match.group(group)
        return func(s)

    return _match


_match_group_lower = _transform_group(str.lower)
_match_group_upper = _transform_group(str.upper)


class Inflections(object):
    '''.. class:: Inflections(locale : str)

    A singleton instance of this class is yielded by :meth:`Inflections.instance`,
    which can then be used to specify additional inflection rules. If passed an
    optional locale, rules for other languages can be specified. The default
    locale is derrived from :func:`locale.getdefaultlocale`. Only rules for English
    are provided. This class implements the context manager protocol so it can
    be used in `with` blocks.

        >>> with Inflections.instance('en_US') as inst:
        ...     inst.acronym('HTTP')
        ...
        ...     inst.plural(_ci_re(r'^(ox)$'), r'\\1en')
        ...     inst.singular(_ci_re(r'^(ox)en'), r'\\1')
        ...
        ...     inst.irregular('octopus', 'octopi')
        ...
        ...     inst.uncountable('equipment')

    New rules are added at the top. So in the example above, the irregular rule
    for octopus will now be the first of the pluralization and singularization
    rules that is run. This guarantees that your rules run before any of the
    rules that may already have been pre-loaded.

    :param str locale: The localization this object represents.
    '''
    __locale_cache = {}
    __scopes = ('acronyms', 'humans', 'plurals', 'singulars', 'uncountables')
    __camelize_pattern = r'\A(?:%s(?=\b|[A-Z_])|\w)'
    __underscore_pattern = r'(?:(?<=([A-Za-z\d]))|\b)(%s)(?=\b|[^a-z])'

    def __init__(self, locale):
        self.locale = locale
        self.acronyms = []
        self.humans = []
        self.plurals = []
        self.singulars = []
        self.uncountables = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    @classmethod
    def instance(cls, locale=None):
        '''.. method:: instance([locale : str]) -> Inflections

        Fetch a singleton instance of the `Inflections` collection for the
        specified locale.

        :param str locale: The binding localization; if not provided, defaults to
            :func:`locale.getdefaultlocale`.
        :returns: A singleton instance of the `Inflections` collection.
        :rtype: inflection.Inflections
        '''
        if locale is None:
            locale = getdefaultlocale()[0]

        return cls.__locale_cache.setdefault(locale, cls(locale))

    def clear(self, scope='all'):
        '''.. method:: clear([scope : str])

        Clear this instance's lists. You may specify a scope, one of `acronyms`,
        `humans`, `plurals`, `singulars`, `uncountables`, and `all`. If not provided,
        defaults to `all`.

        :param str scope: The scope to clear.
        '''
        if scope == 'all':
            return [self.clear(x) for x in self.__scopes]

        assert scope in self.__scopes, 'Invalid scope!'
        setattr(self, scope, [])

    def irregular(self, singular, plural):
        '''.. method(singular : str, plural : str)

        Add an irregular inflection case.
        '''
        self.countable(singular)
        self.countable(plural)

        s0, stail = singular[0], singular[1:]
        p0, ptail = plural[0], plural[1:]

        if s0.upper() == p0.upper():
            fmt = r'(%s)%s\Z'
            for x in (singular, plural):
                pattern = fmt % (x[0], x[1:])
                pattern = _ci_re(pattern)
                self.singular(pattern, r'\1' + stail)
                self.plural(pattern, r'\1' + ptail)
        else:
            fmt = r'%s%s\Z'
            strs = (singular, plural)
            mods = (str.upper, str.lower)
            for x, mod in itertools.product(strs, mods):
                x0, xtail = x[0], x[1:]
                pattern = fmt % (mod(x0), _ci_re(xtail))
                self.singular(pattern, mod(s0) + stail)
                self.plural(pattern, mod(p0) + ptail)

    def acronym(self, *words):
        def _map(word):
            # sort length descending
            return ~len(word), word.lower(), word

        self.acronyms.extend(map(_map, words))
        self.acronyms.sort()
        self.__update_acronym_pattern()

    #region acronym_pattern
    def __define_acronym_pattern(self):
        if self.acronyms:
            items = map(itemgetter(2), self.acronyms)
            items = map(re.escape, items)
            rx = r'(?:%s)' % ('|'.join(items), )
        else:
            rx = r'(?=a)b'

        self.__acronym_pattern = rx  # type: str
        return rx

    def __get_acronym_pattern(self):
        try:
            return self.__acronym_pattern
        except AttributeError:
            return self.__define_acronym_pattern()

    def __update_acronym_pattern(self):
        try:
            self.__acronym_pattern
        except AttributeError:
            # don't update if we've never generated it
            pass
        else:
            self.__define_acronym_pattern()

    @property
    def acronym_pattern(self):
        return self.__get_acronym_pattern()

    @property
    def acronyms_camelize_pattern(self):
        return self.__camelize_pattern % (self.__get_acronym_pattern(), )

    @property
    def acronyms_underscore_pattern(self):
        return self.__underscore_pattern % (self.__get_acronym_pattern(), )

    #endregion

    def human(self, rule, replacement):
        item = rule, replacement
        self.humans.insert(0, item)
        return item

    def plural(self, rule, replacement):
        self.countable(rule)
        self.countable(replacement)

        item = rule, replacement
        self.plurals.insert(0, item)
        return item

    def singular(self, rule, replacement):
        self.countable(rule)
        self.countable(replacement)

        item = rule, replacement
        self.singulars.insert(0, item)
        return item

    def uncountable(self, *words):
        def _map(word):
            return ~len(word), word.lower(), _as_re(word)

        self.uncountables.extend(map(_map, words))
        self.uncountables.sort()

    def countable(self, word):
        _len = len(word)
        search = word.lower()
        for idx, (item_len, item_key, _item_re) in enumerate(self.uncountables):
            if _len < ~item_len:
                continue
            if _len == ~item_len and item_key == search:
                del self.uncountables[idx]
                return
            if ~item_len < _len:
                return

    def is_uncountable(self, word):
        items = map(itemgetter(2), self.uncountables)
        items = map(re.search, items, itertools.repeat(word))
        return any(items)

    def apply_inflections(self, word, rules, apply_uncountable=True):
        if not word or apply_uncountable and self.is_uncountable(word):
            return word

        for rule, replacement in rules:
            word, matches = re.subn(rule, replacement, word, 1)
            if matches:
                break

        return word

    def lookup_acronym(self, term):
        term = str(term).lower()
        term_len = len(term)
        for _len, key, word in self.acronyms:
            if term_len < _len:
                continue
            if term_len == _len and term == key:
                return word
            if _len < term_len:
                return None


def pluralize(word, locale=None):
    inst = Inflections.instance(locale)
    return inst.apply_inflections(word, inst.plurals)


def singularize(word, locale=None):
    inst = Inflections.instance(locale)
    return inst.apply_inflections(word, inst.singulars)


def camelize(string, uppercase_first_letter=True, locale=None):
    inst = Inflections.instance(locale)

    def cap(text):
        return inst.lookup_acronym(text) or text.capitalize()

    def hump(match):
        m0 = match.group(1) or ''
        mtail = cap(match.group(2))
        return m0 + mtail

    if uppercase_first_letter:
        string = re.sub(r'^[a-z\d]*', _transform_group(cap), string, 1)
    else:
        string = re.sub(inst.acronyms_camelize_pattern, _match_group_lower, string, 1)

    string = re.sub(_ci_re(r'(?:_|(\/))([a-z\d]*)'), hump, string)
    return string


def underscore(string, locale=None):
    inst = Inflections.instance(locale)

    def part(match):
        m0 = match.group(1) or '_'
        mtail = match.group(2).lower()
        return m0 + mtail

    string = re.sub(inst.acronyms_underscore_pattern, part, string)
    string = re.sub(r'([A-Z\d]+)([A-Z][a-z])', r'\1_\2', string)
    string = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', string)
    string = string.replace('-', '_')
    return string.lower()


def humanize(string, capitalize=True, keep_id_suffix=False, locale=None):
    inst = Inflections.instance(locale)

    def lower(match):
        res = match.group().lower()
        return inst.lookup_acronym(res) or res

    string = inst.apply_inflections(string, inst.humans, False)
    string = re.sub(r'\A_+', '', string, 1)
    if not keep_id_suffix:
        string = re.sub(r'_id\Z', '', string)

    string = string.replace('_', ' ')
    string = re.sub(_ci_re(r'([a-z\d]*)'), lower, string)
    if capitalize:
        string = upcase_first(string)

    return string


def upcase_first(string):
    return re.sub(r'\A\w', _match_group_upper, string, 1)


def titleize(string, keep_id_suffix=False, locale=None):
    string = underscore(string, locale)
    string = humanize(string, True, keep_id_suffix, locale)
    string = re.sub(r'\b(?<!\w[\'’`])[a-z]', _match_group_upper, string)
    return string


def tableize(string, locale=None):
    string = underscore(string, locale)
    string = pluralize(string, locale)
    return string


def classify(string, locale=None):
    string = re.sub(r'.*\.', '', string)
    string = singularize(string, locale)
    string = camelize(string, True, locale)
    return string


def dasherize(word):
    '''Replace underscores with dashes in the string.

    Example::

        >>> dasherize('puni_puni')
        'puni-puni'

    '''
    return word.replace('_', '-')


def demodulize(string, separator='.'):
    # ruby version splits on ::, but I figured python would rather .
    try:
        idx = string.rindex(separator)
    except ValueError:
        return string
    else:
        return string[idx + len(separator):]


def deconstantize(string, separator='.'):
    try:
        idx = string.rindex(separator)
    except ValueError:
        return ''
    else:
        return string[:idx]


def foreign_key(string, separate_class_name_and_id_with_underscore=True, locale=None):
    string = demodulize(string)
    string = underscore(string, locale)
    if separate_class_name_and_id_with_underscore:
        string = string + '_'
    string = string + 'id'
    return string


def ordinal(number):
    '''
    Return the suffix that should be added to a number to denote the position
    in an ordered sequence such as 1st, 2nd, 3rd, 4th.

    Examples::

        >>> ordinal(1)
        'st'
        >>> ordinal(2)
        'nd'
        >>> ordinal(1002)
        'nd'
        >>> ordinal(1003)
        'rd'
        >>> ordinal(-11)
        'th'
        >>> ordinal(-1021)
        'st'

    '''
    number = abs(int(number))
    if number % 100 in (11, 12, 13):
        return 'th'
    else:
        return {
            1: 'st',
            2: 'nd',
            3: 'rd',
        }.get(number % 10, 'th')


def ordinalize(number):
    '''
    Turn a number into an ordinal string used to denote the position in an
    ordered sequence such as 1st, 2nd, 3rd, 4th.

    Examples::

        >>> ordinalize(1)
        '1st'
        >>> ordinalize(2)
        '2nd'
        >>> ordinalize(1002)
        '1002nd'
        >>> ordinalize(1003)
        '1003rd'
        >>> ordinalize(-11)
        '-11th'
        >>> ordinalize(-1021)
        '-1021st'

    '''
    return '%s%s' % (number, ordinal(number))


def parameterize(string, separator='-', preserve_case=False):
    string = transliterate(string)
    string = re.sub(_ci_re(r'[^a-z0-9_-]+'), separator, string)

    if separator:
        # wrap sep in a group to allow multi-len separator ':='
        # why you'd do that isn't really clear
        sep_re = '(?:%s)' % (re.escape(separator), )
        duplicate_sep_re = r'%s{2,}' % (sep_re, )
        leading_trailing_sep_re = r'^%s|%s$' % (sep_re, sep_re)
        string = re.sub(duplicate_sep_re, separator, string)
        string = re.sub(leading_trailing_sep_re, '', string)

    if not preserve_case:
        string = string.lower()

    return string


def transliterate(string):
    '''
    Replace non-ASCII characters with an ASCII approximation. If no
    approximation exists, the non-ASCII character is ignored. The string must
    be ``unicode``.

    Examples::

        >>> transliterate(u'älämölö')
        u'alamolo'
        >>> transliterate(u'Ærøskøbing')
        u'rskbing'

    '''
    normalized = normalize('NFKD', string)
    return normalized.encode('ascii', 'ignore').decode('ascii')


with Inflections.instance('en_US') as inst:
    inst.acronym(
        'GNU', 'HTTP', 'I18N', 'JSON', 'L10N', 'NaN', 'PCIe', 'PoE', 'PPPoA', 'PPPoE', 'QoS', 'REST', 'RESTful', 'RSS',
        'SOAP', 'VoIP', 'WebDAV', 'WiFi', 'WinRT', 'XML', 'XMLRPC', 'YAML'
    )

    from string import ascii_uppercase
    for c in ascii_uppercase:
        inst.acronym(c + 'aaS')

    inst.plural(_ci_re(r'$'), r's')
    inst.plural(_ci_re(r's$'), r's')
    inst.plural(_ci_re(r'^(ax|test)is$'), r'\1es')
    inst.plural(_ci_re(r'(octop|vir)us$'), r'\1i')
    inst.plural(_ci_re(r'(octop|vir)i$'), r'\1i')
    inst.plural(_ci_re(r'(alias|status)$'), r'\1es')
    inst.plural(_ci_re(r'(bu)s$'), r'\1ses')
    inst.plural(_ci_re(r'(buffal|potat|tomat)o$'), r'\1oes')
    inst.plural(_ci_re(r'([ti])um$'), r'\1a')
    inst.plural(_ci_re(r'([ti])a$'), r'\1a')
    inst.plural(_ci_re(r'sis$'), r'ses')
    inst.plural(_ci_re(r'(?:([^f])fe|([lr])f)$'), r'\1\2ves')
    inst.plural(_ci_re(r'(hive)$'), r'\1s')
    inst.plural(_ci_re(r'([^aeiouy]|qu)y$'), r'\1ies')
    inst.plural(_ci_re(r'(x|ch|ss|sh)$'), r'\1es')
    inst.plural(_ci_re(r'(matr|vert|ind)(?:ix|ex)$'), r'\1ices')
    inst.plural(_ci_re(r'^(m|l)ouse$'), r'\1ice')
    inst.plural(_ci_re(r'^(m|l)ice$'), r'\1ice')
    inst.plural(_ci_re(r'^(ox)$'), r'\1en')
    inst.plural(_ci_re(r'^(oxen)$'), r'\1')
    inst.plural(_ci_re(r'(quiz)$'), r'\1zes')

    inst.singular(_ci_re(r's$'), r'')
    inst.singular(_ci_re(r'(ss)$'), r'\1')
    inst.singular(_ci_re(r'(n)ews$'), r'\1ews')
    inst.singular(_ci_re(r'([ti])a$'), r'\1um')
    inst.singular(_ci_re(r'((a)naly|(b)a|(d)iagno|(p)arenthe|(p)rogno|(s)ynop|(t)he)(sis|ses)$'), r'\1sis')
    inst.singular(_ci_re(r'(^analy)(sis|ses)$'), r'\1sis')
    inst.singular(_ci_re(r'([^f])ves$'), r'\1fe')
    inst.singular(_ci_re(r'(hive)s$'), r'\1')
    inst.singular(_ci_re(r'(tive)s$'), r'\1')
    inst.singular(_ci_re(r'([lr])ves$'), r'\1f')
    inst.singular(_ci_re(r'([^aeiouy]|qu)ies$'), r'\1y')
    inst.singular(_ci_re(r'(s)eries$'), r'\1eries')
    inst.singular(_ci_re(r'(m)ovies$'), r'\1ovie')
    inst.singular(_ci_re(r'(x|ch|ss|sh)es$'), r'\1')
    inst.singular(_ci_re(r'^(m|l)ice$'), r'\1ouse')
    inst.singular(_ci_re(r'(bus)(es)?$'), r'\1')
    inst.singular(_ci_re(r'(o)es$'), r'\1')
    inst.singular(_ci_re(r'(shoe)s$'), r'\1')
    inst.singular(_ci_re(r'(cris|test)(is|es)$'), r'\1is')
    inst.singular(_ci_re(r'^(a)x[ie]s$'), r'\1xis')
    inst.singular(_ci_re(r'(octop|vir)(us|i)$'), r'\1us')
    inst.singular(_ci_re(r'(alias|status)(es)?$'), r'\1')
    inst.singular(_ci_re(r'^(ox)en'), r'\1')
    inst.singular(_ci_re(r'(vert|ind)ices$'), r'\1ex')
    inst.singular(_ci_re(r'(matr)ices$'), r'\1ix')
    inst.singular(_ci_re(r'(quiz)zes$'), r'\1')
    inst.singular(_ci_re(r'(database)s$'), r'\1')

    inst.irregular('zombie', 'zombies')
    inst.irregular('sex', 'sexes')
    inst.irregular('person', 'people')
    inst.irregular('move', 'moves')
    inst.irregular('man', 'men')
    inst.irregular('human', 'humans')
    inst.irregular('cow', 'kine')
    inst.irregular('child', 'children')

    inst.uncountable(
        'equipment', 'fish', 'information', 'jeans', 'money', 'police', 'rice', 'series', 'sheep', 'species'
    )
