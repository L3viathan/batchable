import sys
import gc
from types import MethodType, FrameType
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        self.cache = OrderedDict()
        self.capacity = capacity

    def __getitem__(self, key):
        if key not in self.cache:
            return -1
        else:
            self.cache.move_to_end(key)
            return self.cache[key]

    def __contains__(self, key):
        return key in self.cache

    def __setitem__(self, key, value):
        self.cache[key] = value
        self.cache.move_to_end(key)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)


class Proxy:
    def __init__(self):
        self.call = lambda x: x

    def replace(self, target):
        for referrer in gc.get_referrers(self):
            if isinstance(referrer, dict):
                for key in list(referrer):
                    if referrer[key] is self:
                        referrer[key] = self.call(target)
            elif isinstance(referrer, list):
                for i, element in enumerate(referrer):
                    if element is self:
                        referrer[i] = self.call(target)
            elif isinstance(referrer, (FrameType, MethodType)):
                pass
            elif isinstance(referrer, tuple):
                continue  # damn, segfaults :D
                # for i, element in enumerate(referrer):
                #     if element is self:
                #         new = self.call(target)
                #         element_ptr = ctypes.c_longlong.from_address(id(self) + (3 + i) * 8)
                #         element_ptr.value = id(new)

                #         # fix reference counts:
                #         ctypes.c_longlong.from_address(id(new)).value += 1
                #         ctypes.c_longlong.from_address(id(self)).value -= 1
                #         break
            else:
                print("don't know how to patch", type(referrer))

    def __getitem__(self, item):
        self.call = lambda x, call=self.call: call(x)[item]
        return self

    def __getattr__(self, item):
        self.call = lambda x, call=self.call: getattr(call(x), item)
        return self

    def __call__(self, *args, **kwargs):
        self.call = lambda x, call=self.call: call(x)(*args, **kwargs)
        return self


class able:
    def __init__(self, batch_size):
        self.batch_size = batch_size
        self.unresolved = {}
        self.resolver = None

    def __call__(self, fn):
        self.resolver = fn

        def wrapper(id):
            frame = sys._getframe()
            while "my_ables" not in frame.f_locals:
                frame = frame.f_back
                if not frame:
                    result = self.resolver([id])[id]
                    return result
            frame.f_locals["my_ables"].add(self)
            if len(self.unresolved) >= self.batch_size:
                self.resolve()
            p = Proxy()
            self.unresolved[id] = p
            return p

        return wrapper

    def resolve(self):
        ids = set(self.unresolved.keys())
        result = self.resolver(ids)
        for id, p in self.unresolved.items():
            p.replace(result[id])
        self.unresolved = {}


def ed(fn):
    def wrapper(objs):
        my_ables = set()
        for obj in objs:
            yield fn(obj)
        for a in my_ables:
            a.resolve()

    fn.s = wrapper
    return fn
