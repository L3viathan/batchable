import batch
from functools import lru_cache


@batch.able(batch_size=10)
def shop_lookup(shop_ids):
    print("Looking up shops:", shop_ids)
    return {
        shop_id: {
            "id": shop_id,
            "name": f"Name of shop {shop_id}",
            "url": f"http://shop{shop_id}.com",
        }
        for shop_id in shop_ids
    }


@lru_cache(maxsize=None)
@batch.able(batch_size=3)
def brand_lookup(brand_ids):
    print("Looking up brands:", brand_ids)
    return {
        brand_id: {
            "id": brand_id,
            "name": ["Apple", "Google", "Samsung", "Huawei"][brand_id],
        }
        for brand_id in brand_ids
    }



@batch.ed
def transform_offer(offer):
    shop = shop_lookup(offer["shop_id"])
    return {
        "id": offer["offer_id"],
        "shop_name": shop["name"],
        "shop_url": shop["url"],
        "brand_name": brand_lookup(offer["brand_id"])["name"],
    }


print(shop_lookup(42))

source = [{"offer_id": offer_id, "shop_id": offer_id + 100, "brand_id": offer_id % 4} for offer_id in range(23)]
print(list(transform_offer.s(source)))
