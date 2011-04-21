from __future__ import absolute_import, with_statement

from functools import wraps
from threading import Lock

from celery.datastructures import LRUCache

KEYWORD_MARK = object()


def memoize(maxsize=None, Cache=LRUCache):

    def _memoize(fun):
        mutex = Lock()
        cache = Cache(limit=maxsize)

        @wraps(fun)
        def _M(*args, **kwargs):
            key = args + (KEYWORD_MARK, ) + tuple(sorted(kwargs.iteritems()))
            try:
                with mutex:
                    value = cache[key]
            except KeyError:
                value = fun(*args, **kwargs)
                _M.misses += 1
                with mutex:
                    cache[key] = value
            else:
                _M.hits += 1
            return value

        def clear():
            """Clear the cache and reset cache statistics."""
            cache.clear()
            _M.hits = _M.misses = 0

        _M.hits = _M.misses = 0
        _M.clear = clear
        _M.original_func = fun
        return _M

    return _memoize
