# batchable

Allows hiding the batching logic of requests.

```bash
pip install batchable
```

This is the result of a learning day @ solute, together with
[@digitalarbeiter](https://github.com/digitalarbeiter).

## Idea

We are often faced with the following situation:

- A stream of objects has to be processed
- During this process, some kind of lookup has to be made

As an example, consider this mockup of an e-commerce system processing offers
for articles:

```python
def transform_offer(offer):
    return {
        "id": offer["offer_id"],
        "shop_id": offer["shop_id"],
    }

processed_offers = [transform_offer(offer) for offer in unprocessed_offers]
```

So far, this is straightforward. Now consider the case where you want to add
the name of the shop referenced by ID. This name is not stored inside the
unprocessed offer, but instead has to be retrieved from a (different) database:

```python
def transform_offer(offer):
    return {
        "id": offer["offer_id"],
        "shop_name": lookup_shop(offer["shop_id"])["name"],
    }

def lookup_shop(shop_id):
    # returns e.g. {"id": 23, "name": "Fancy shop"}
    return dict(
        db.execute(
            "SELECT id, name FROM shops WHERE id={id}",
            id=shop_id,
        ).fetchone(),
    )
```

Again, this works, but it has a major downside: For every offer that is
processed, a new roundtrip is made to the database. We also would do the exact
same queries several times, if some offers share the same shop ID (which is
very likely). This second problem is solvable by caching the function, e.g. via
`functools.lru_cache`. But the main problem (one request per offer) remains.

The solution to this problem is to add batching: You somehow have to collect
the shop IDs somewhere, and only make a request once there are _n_ shop IDs
being requested. Doing this is non-trivial, but also not terribly difficult.
The problem with this solution is that you now have to restructure your code
quite a bit. Maybe you have to iterate over the offers twice; once to get _all_
shop IDs, and then again to do the actual processing. Maybe you'd do it the
other way around, where you do several passes (first put only shop IDs in the
offers while also putting them in some kind of queue, then process the queue,
and finally enrich the half-processed offers with shop names.

------

This project aims to solve this issue, by allowing you to write your code just
like you normally would, and doing nasty things behind the scenes to enable
batching that you don't see. First, you import the library:

```python
import batch
```

Then you decorate the function you want to batch with `batch.able`, while
changing it to handle _several_ IDs:

```python
@batch.able(batch_size=10)
def lookup_shop(shop_ids):
    return {
        row["id"]: dict(row)
        for row in db.execute(
            "SELECT id, name FROM shops WHERE id=ANY({ids})",
            ids=tuple(shop_id),
        ),
    }
```

You still call this function with a single shop ID, with no functional changes.
You can, however, also call it inside a context manager:

```python
with batch.ed:
    processed_offers = [transform_offer(offer) for offer in unprocessed_offers]
```

This is again functionally identical, _but_ `lookup_shop` gets called with (up
to) 10 shop IDs at a time. You can also provide a `default=` argument to the
decorator to set a default value for missing rows (otherwise missing rows will
raise an exception).

If you want, you can also add a cache to this function — make sure to add it
_on top_ of the `@batch.able` decorator, so it caches per ID.


## Caveats

The way this works is by having the lookup function return `Proxy` objects that
are later (either when the batch size is reached, or when leaving the context
manager) magically replaced by the actual object. The proxy knows about
indexing and attribute access, so that will just work as well. The level of
magic means however that there are limitations to this technique:

- **CPython only:** proxies are replaced with a devious technique involving the
  reference-counting garbage collector, meaning this won't work on
  implementations without one (e.g. PyPy).
- **no thread-safety:** to be honest, it will _probably usually_ just work, but
  we sure as hell don't guarantee it. We do a `gc.collect()` immediately before
  asking the GC for references to the proxy, but in the meantime a different
  thread could have decremented the reference count, meaning we could get
  half-dead objects that haven't been reaped yet.
- **no tuples:** we only replace references in lists and dicts (including
  instance dictionaries). That means that we are not able to replace references
  in tuples. It would technically be possible to do this, but the way this
  library works is surprising enough; we didn't want to violate the "immutable
  objects can't be changed" rule.
- **IDs must be hashable:** probably a no-brainer, but the IDs used as
  arguments to the lookup functions must be hashable. They almost always are
  anyways.
- **no intermediate use:** This is the most dangerous foot-gun. Make sure not
  to use results of calling `transform_offer` _until you have left the context
  manager_, because the proxies may not all have been replaced yet.


## Complete example

A more complete example can be seen in the file `usage.py`. When executing it,
observe where the `Proxy` objects are still shown, and where they have
disappeared.
