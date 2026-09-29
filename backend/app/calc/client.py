"""Клиент calc-воркеров. Несколько воркеров (CALC_URLS) — запрос идёт в наименее занятый."""
import asyncio
import hashlib
import json
from collections import OrderedDict

import httpx

from .. import settings


class CalcUnavailable(Exception):
    pass


_inflight = {u: 0 for u in settings.CALC_URLS}
_cache: "OrderedDict[str, dict]" = OrderedDict()
_CACHE_MAX = 500
_lock = asyncio.Lock()


def _pick():
    return min(_inflight, key=_inflight.get)


async def _post(path: str, body: dict) -> dict:
    url = _pick()
    _inflight[url] += 1
    try:
        return await _post_to(url, path, body)
    finally:
        _inflight[url] -= 1


async def recalc(model_version: str, writes: list[dict], reads: list[dict]) -> dict:
    key = hashlib.sha1(json.dumps([model_version, writes], sort_keys=True).encode()).hexdigest()
    async with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return {**_cache[key], "cached": True}
    res = await _post("/recalc", {"model_version": model_version, "writes": writes, "reads": reads})
    async with _lock:
        _cache[key] = res
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)
    return res


async def preload(model_version: str, reads: list[dict]) -> dict:
    """Загрузить версию во все воркеры; вернуть значения первого (для сверки с кэшем Excel)."""
    results = await asyncio.gather(
        *[_post_to(u, "/load", {"model_version": model_version, "reads": reads}) for u in settings.CALC_URLS],
        return_exceptions=True,
    )
    for r in results:
        if not isinstance(r, Exception):
            return r
    raise results[0]


async def _post_to(url, path, body):
    try:
        async with httpx.AsyncClient(timeout=settings.CALC_TIMEOUT_S) as c:
            r = await c.post(url + path, json=body)
    except httpx.HTTPError as e:
        raise CalcUnavailable(f"calc-воркер {url} недоступен: {e.__class__.__name__}") from e
    if r.status_code != 200:
        raise CalcUnavailable(f"calc-воркер {url}: {r.status_code} {r.text[:200]}")
    return r.json()
