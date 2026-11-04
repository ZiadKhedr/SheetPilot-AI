"""Bound request bodies before multipart parsing can spool large files to disk."""
from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    def __init__(self, app, upload_limit=10 * 1024 * 1024 + 65536, json_limit=1_000_000):
        self.app, self.upload_limit, self.json_limit = app, upload_limit, json_limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"} or not scope["path"].startswith("/api/"):
            return await self.app(scope, receive, send)
        limit = ((64 * 1024 * 1024 + 65536) if scope["path"] == "/api/backups/restore" else
                 self.upload_limit if scope["path"].endswith(("/uploads", "/versions")) else self.json_limit)
        headers = dict(scope["headers"])
        try:
            declared = int(headers.get(b"content-length", b"0"))
            if declared < 0:
                raise ValueError()
        except ValueError:
            return await JSONResponse({"detail": "Invalid Content-Length."}, status_code=400)(scope, receive, send)
        if declared > limit:
            return await JSONResponse({"detail": "Request exceeds the body size limit."}, status_code=413)(scope, receive, send)
        messages, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > limit:
                return await JSONResponse({"detail": "Request exceeds the body size limit."}, status_code=413)(scope, receive, send)
            messages.append(message)
            if not message.get("more_body", False):
                break
        iterator = iter(messages)
        async def replay():
            try:
                return next(iterator)
            except StopIteration:
                return await receive()
        return await self.app(scope, replay, send)
