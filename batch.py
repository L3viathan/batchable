import sys
import gc
from types import MethodType, FrameType


class Proxy:
    def __init__(self, call=None, family=None):
        self.call = call or (lambda x: x)
        self.family = family
        if family is not None:
            family.append(self)


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
            elif isinstance(referrer, (FrameType, MethodType, tuple)):
                pass
            else:
                print("don't know how to patch", type(referrer))

    def __getitem__(self, item):
        return Proxy(call=(lambda x, call=self.call: call(x)[item]), family=self.family)

    def __getattr__(self, item):
        return Proxy(call=(lambda x, call=self.call: getattr(call(x), item)), family=self.family)

    def __call__(self, *args, **kwargs):
        return Proxy(call=(lambda x, call=self.call: call(x)(*args, **kwargs)), family=self.family)


class able:
    def __init__(self, batch_size):
        self.batch_size = batch_size
        self.unresolved = {}
        self.resolver = None

    def __call__(self, fn):
        self.resolver = fn

        def wrapper(id):
            frame = sys._getframe()
            while "my_ables_raeT9ahL" not in frame.f_locals:
                frame = frame.f_back
                if not frame:
                    result = self.resolver([id])[id]
                    return result
            frame.f_locals["my_ables_raeT9ahL"].add(self)
            if len(self.unresolved) >= self.batch_size:
                self.resolve()
            return Proxy(family=self.unresolved.setdefault(id, []))

        return wrapper

    def resolve(self):
        ids = set(self.unresolved.keys())
        result = self.resolver(ids)
        for id, proxies in self.unresolved.items():
            for proxy in proxies:
                proxy.replace(result[id])
        self.unresolved = {}


def ed(fn):
    def wrapper(objs):
        my_ables_raeT9ahL = set()
        for obj in objs:
            yield fn(obj)
        for a in my_ables_raeT9ahL:
            a.resolve()

    fn.s = wrapper
    return fn
