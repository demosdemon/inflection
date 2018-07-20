Inflection
==========

Inflection is a string transformation library.  It singularizes and pluralizes
English words, and transforms strings from CamelCase to underscored_string.
Inflection is a port of `Ruby on Rails`_' `inflector`_ to Python.

.. _Ruby on Rails: http://rubyonrails.org
.. _inflector: http://api.rubyonrails.org/classes/ActiveSupport/Inflector.html


Installation
------------

Use pip to install from PyPI::

    pip install inflection


Contributing
------------

To contribute to Inflector `create a fork`_ on GitHub. Clone your fork, make
some changes, and submit a pull request.

.. _create a fork: https://github.com/jpvanhal/inflection/fork_select


API Documentation
-----------------

.. module:: inflection

.. autoclass:: Inflections
    :members:
    :undoc-members:

.. autofunction:: camelize
.. autofunction:: classify
.. autofunction:: dasherize
.. autofunction:: deconstantize
.. autofunction:: demodulize
.. autofunction:: foreign_key
.. autofunction:: humanize
.. autofunction:: ordinal
.. autofunction:: ordinalize
.. autofunction:: parameterize
.. autofunction:: pluralize
.. autofunction:: singularize
.. autofunction:: tableize
.. autofunction:: titleize
.. autofunction:: transliterate
.. autofunction:: underscore
.. autofunction:: upcase_first

.. include:: ../CHANGES.rst

License
-------

.. include:: ../LICENSE
