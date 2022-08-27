import sys
import gc
import warnings
from types import MethodType, FrameType


class Proxy:
    def __init__(self, call=None, family=None, referent_name="?"):
        self.call = call or (lambda x: x)
        self.family = family
        if family is not None:
            family.append(self)
        self.referent_name = referent_name

    def __repr__(self):
        return f"<Proxy:{self.referent_name}>"

    def replace(self, target):
        gc.collect()  # so we can never get half-dead objects
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
                warnings.warn(f"Don't know how to patch {type(referrer)}")

    def __getitem__(self, item):
        return Proxy(
            call=(lambda x, call=self.call: call(x)[item]),
            family=self.family,
            referent_name=f"{self.referent_name}[{item!r}]",
        )

    def __getattr__(self, attr):
        return Proxy(
            call=(lambda x, call=self.call: getattr(call(x), attr)),
            family=self.family,
            referent_name=f"{self.referent_name}.{attr}",
        )

    def __call__(self, *args, **kwargs):
        return Proxy(
            call=(lambda x, call=self.call: call(x)(*args, **kwargs)),
            family=self.family,
            referent_name=f"{self.referent_name}(...)",
        )


missing = object()


class able:
    def __init__(self, batch_size, *, default=missing):
        self.batch_size = batch_size
        self.unresolved = {}
        self.resolver = None
        self.default = default

    def __call__(self, fn):
        self.resolver = fn

        def wrapper(id):
            frame = sys._getframe()
            while "my_ables_raeT9ahL" not in frame.f_locals:
                frame = frame.f_back
                if not frame:
                    result = self.resolver({id})[id]
                    return result
            frame.f_locals["my_ables_raeT9ahL"].add(self)
            if len(self.unresolved) >= self.batch_size:
                self.resolve()
            return Proxy(
                family=self.unresolved.setdefault(id, []),
                referent_name=f"{self.resolver.__name__}({id})",
            )

        return wrapper

    def resolve(self):
        ids = set(self.unresolved.keys())
        result = self.resolver(ids)
        for id, proxies in self.unresolved.items():
            for proxy in proxies:
                if self.default is not missing and id not in result:
                    proxy.replace(self.default)
                else:
                    proxy.replace(result[id])
        self.unresolved = {}


@type.__call__
class ed:
    def __init__(self):
        self.batchables = []

    def __enter__(self):
        self.batchables.append(set())
        sys._getframe().f_back.f_locals["my_ables_raeT9ahL"] = self.batchables[-1]

    def __exit__(self, exc, exct, tb):
        for batchable in self.batchables.pop():
            batchable.resolve()
