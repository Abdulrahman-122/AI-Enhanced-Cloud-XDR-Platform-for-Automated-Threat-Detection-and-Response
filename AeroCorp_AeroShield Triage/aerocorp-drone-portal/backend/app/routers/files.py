import os
import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from ..config import settings
from ..logging_setup import log_event
from ..security import client_ip
from ..util import flag_suspicious

router = APIRouter()

SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9\-]{0,120}\.txt$")


@router.get("/api/datasheets/download")
def download(request: Request, file: str):
    ip = client_ip(request)
    flag_suspicious("/api/datasheets/download", ip, file=file)

    if settings.vuln_mode:
        path = os.path.join(str(settings.datasheet_dir), file)
        log_event("file_download", client_ip=ip, requested=file[:300])
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        with open(path, "rb") as handle:
            data = handle.read()
        name = os.path.basename(file) or "datasheet.txt"
        return Response(
            content=data,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{name}"'},
        )

    if not SAFE_NAME.match(file):
        raise HTTPException(status_code=404, detail="Datasheet not found")
    base = settings.datasheet_dir.resolve()
    path = (base / file).resolve()
    if base not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Datasheet not found")
    log_event("file_download", client_ip=ip, requested=file)
    return Response(
        content=path.read_bytes(),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{path.name}"', "X-Content-Type-Options": "nosniff"},
    )
