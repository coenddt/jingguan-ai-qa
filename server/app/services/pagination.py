"""列表分页公共查询：count + 排序分页 + id 映射一次封装（3 处路由同构聚合）"""

from app.db.mongo_store import store


async def paged_query(model: str, cond: dict, page: int, page_size: int,
                      fields: str, sort: dict | None = None) -> dict:
    """库内分页 → {'items': [...(id 替换 _id)], 'total': n}；page 从 1 起"""
    sort = sort or {'createdAt': -1}
    total = await store.count(model, cond)
    rows = await store.query(
        f'{model}($condition:@c0,$sort:@s0,$skip:@sk,$limit:@l) {{ {fields} }}',
        {'c0': cond, 's0': sort, 'sk': (page - 1) * page_size, 'l': page_size},
    )
    return {'items': [{**r, 'id': r['_id']} for r in rows], 'total': total}
