from fastapi import Depends, File, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from base64 import b64encode
from typing import Literal

from .backups import ARCHIVE_LIMIT, create_backup, restore_backup
from .store import Problem, uid


def register_workspace_routes(app, store, auth):
    @app.get("/api/backups/export")
    @app.post("/api/backups/export")
    def export(encoding: Literal['binary', 'base64'] = 'binary', actor=Depends(auth)):
        if actor == "reader":
            raise Problem("Only the workspace owner can export an installation backup.", 403)
        result = create_backup(store)
        if encoding == 'base64':
            return {'name':'SheetPilot-Backup.zip', 'content':b64encode(result).decode('ascii')}
        directory = store.root / 'backups'
        directory.mkdir(exist_ok=True)
        path = directory / (uid() + '.zip')
        path.write_bytes(result)
        return FileResponse(path, media_type="application/zip", filename="SheetPilot-Backup.zip",
                            background=BackgroundTask(path.unlink, missing_ok=True))

    @app.post("/api/backups/restore", dependencies=[Depends(auth)])
    async def restore(file: UploadFile = File(...)):
        content = await file.read(ARCHIVE_LIMIT + 1)
        await file.close()
        if len(content) > ARCHIVE_LIMIT:
            raise Problem("Restore archive exceeds 64 MiB.", 413)
        return restore_backup(store, content)
