"""Bounded ASGI input handling; complements (does not replace) an edge proxy."""
import asyncio
import json
import math

from starlette.responses import JSONResponse

MAX_BODY_BYTES = 16 * 1024
BODY_TIMEOUT_SECONDS = 3.0


def safe_text(value, limit=200):
    text = str(value).encode('utf-8', errors='replace').decode('utf-8')
    return ''.join(ch if ch.isprintable() else '?' for ch in text)[:limit]


def validation_details(errors):
    # Never reflect raw input/ctx: they may contain nonfinite numbers, secrets,
    # invalid Unicode or arbitrarily long nested values.
    return [{'loc': [part if type(part) is int else safe_text(part, 128)
                      for part in error.get('loc', ())[:8]],
             'msg': safe_text(error.get('msg', 'Некорректное значение.')),
             'type': safe_text(error.get('type', 'value_error'), 80)} for error in errors[:16]]


def strict_json(body):
    def number(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError('nonfinite number')
        return result
    def constant(value):
        raise ValueError('nonstandard JSON number')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    return json.loads(body.decode('utf-8'), parse_float=number, parse_constant=constant, object_pairs_hook=unique)


class InputSafetyMiddleware:
    def __init__(self, app, max_body_bytes=MAX_BODY_BYTES, body_timeout=BODY_TIMEOUT_SECONDS):
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.body_timeout = body_timeout

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)

        async def safe_send(message):
            if message['type'] == 'http.response.start':
                message = dict(message)
                headers = list(message.get('headers', []))
                headers.extend([(b'x-content-type-options', b'nosniff'),
                                (b'referrer-policy', b'no-referrer')])
                if scope.get('path', '').rstrip('/') in ('/recommendations', '/assistant/chat'):
                    headers.append((b'cache-control', b'no-store'))
                message['headers'] = headers
            await send(message)

        async def reject(status, message):
            response = JSONResponse({'detail': message}, status_code=status)
            await response(scope, receive, safe_send)

        # Both public JSON endpoints share the same bounded input policy.
        if scope['method'] != 'POST' or scope.get('path', '').rstrip('/') not in ('/recommendations', '/assistant/chat'):
            return await self.app(scope, receive, safe_send)
        headers = scope.get('headers', [])
        lengths = [value for name, value in headers if name.lower() == b'content-length']
        if lengths:
            if len(lengths) != 1 or not lengths[0].isdigit():
                return await reject(400, 'Некорректный размер запроса.')
            if len(lengths[0]) > 8 or int(lengths[0]) > self.max_body_bytes:
                return await reject(413, 'Запрос превышает лимит 16 КиБ.')
        header_map = dict(headers)
        if header_map.get(b'content-encoding', b'identity').lower() != b'identity':
            return await reject(415, 'Сжатые тела запросов не поддерживаются.')
        if header_map.get(b'content-type', b'').split(b';', 1)[0].strip().lower() != b'application/json':
            return await reject(415, 'Ожидается Content-Type: application/json.')

        async def read_body():
            chunks = []
            size = 0
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return None
                chunk = message.get('body', b'')
                size += len(chunk)
                if size > self.max_body_bytes:
                    raise OverflowError
                chunks.append(chunk)
                if not message.get('more_body', False):
                    return b''.join(chunks)
        try:
            body = await asyncio.wait_for(read_body(), timeout=self.body_timeout)
        except asyncio.TimeoutError:
            return await reject(408, 'Превышено время получения запроса.')
        except OverflowError:
            return await reject(413, 'Запрос превышает лимит 16 КиБ.')
        if body is None:
            return
        if lengths and int(lengths[0]) != len(body):
            return await reject(400, 'Размер тела не соответствует Content-Length.')
        try:
            strict_json(body)
        except (ValueError, UnicodeError, RecursionError):
            return await reject(400, 'Некорректный JSON: проверьте числа, кодировку и повторяющиеся поля.')
        consumed = False
        async def replay():
            nonlocal consumed
            if not consumed:
                consumed = True
                return {'type': 'http.request', 'body': body, 'more_body': False}
            return await receive()
        await self.app(scope, replay, safe_send)
