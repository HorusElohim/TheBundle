from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from ...common.sections import base_context, create_templates, get_logger, get_static_path, get_template_path

NAME = "usd"
TEMPLATE_PATH = get_template_path(__file__)
STATIC_PATH = get_static_path(__file__)
LOGGER = get_logger(NAME)

router = APIRouter()
templates = create_templates(TEMPLATE_PATH)

UPLOAD_DIR = Path("data/usd_uploads")
ALLOWED_USD_EXTS = {".usd", ".usda", ".usdc", ".usdz"}


@router.get("/usd", response_class=HTMLResponse)
async def usd(request: Request):
    context = base_context(request)
    return templates.TemplateResponse(request, "usd.html", context)


@router.post("/usd/upload")
async def upload_usd(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_USD_EXTS:
        raise HTTPException(status_code=400, detail="Unsupported USD file type")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name
    target = UPLOAD_DIR / f"{Path(safe_name).stem}_{uuid4().hex}{suffix}"
    with target.open("wb") as handle:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    await file.close()
    LOGGER.debug("Uploaded USD file to %s", target)
    return {"path": str(target), "name": safe_name, "url": f"/usd/uploads/{target.name}"}


@router.get("/usd/uploads/{filename}")
async def get_uploaded_usd(filename: str):
    if not filename:
        raise HTTPException(status_code=404, detail="Missing file name")
    target = (UPLOAD_DIR / filename).resolve()
    upload_root = UPLOAD_DIR.resolve()
    if upload_root not in target.parents and target != upload_root:
        raise HTTPException(status_code=404, detail="Invalid upload path")
    if not target.exists():
        raise HTTPException(status_code=404, detail="Uploaded file not found")
    return FileResponse(target)


from . import ws  # noqa: E402  # isort:skip
