"""API routes for Explore integration - pulling adapters from cloud and uploading local adapters to cloud."""

import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config import settings
from ..models.database import get_db
from ..models.evaluation import Evaluation
from ..models.style import Style
from ..models.task import Task
from ..schemas.explore import PullAdapterRequest, PullAdapterResponse

router = APIRouter(prefix="/api/explore", tags=["explore"])

EXPLORE_SERVICE_URL = settings.EXPLORE_SERVICE_URL.rstrip("/")


def _pack_adapter_to_zip(adapter_path: str) -> str:
    """Pack adapter directory into a temporary zip file. Returns path to zip."""
    abs_path = Path(adapter_path)
    if not abs_path.is_absolute():
        abs_path = Path(settings.MODELS_DIR).parent / adapter_path

    if not abs_path.exists():
        raise FileNotFoundError(f"Adapter directory not found: {abs_path}")

    # Create temp zip file
    fd, zip_path = tempfile.mkstemp(suffix=".zip", prefix="adapter_")
    os.close(fd)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in abs_path.rglob("*"):
            if file_path.is_file():
                arcname = str(file_path.relative_to(abs_path))
                zf.write(file_path, arcname)

    return zip_path


def _get_evaluation_dict(evaluation: Optional[Evaluation]) -> Optional[dict]:
    """Convert Evaluation model to dict matching cloud EvaluationResults schema."""
    if not evaluation:
        return None
    return {
        "overall_score": evaluation.overall_score,
        "sample_count": evaluation.sample_count,
        "char_retention": evaluation.char_retention,
        "style_score": evaluation.style_score,
        "fluency_score": evaluation.fluency_score,
        "vocab_diversity": evaluation.vocab_diversity,
        "length_ratio": evaluation.length_ratio,
        "bleu_score": evaluation.bleu_score,
        "bert_score": evaluation.bert_score,
        "avg_response_time": evaluation.avg_response_time,
        "samples": json.loads(evaluation.samples) if evaluation.samples else [],
        "comment": evaluation.comment,
    }


@router.post("/pull-adapter", response_model=PullAdapterResponse)
async def pull_adapter_from_cloud(
    request: PullAdapterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Pull an adapter from explore cloud and import into local system."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        meta_resp = await client.get(
            f"{EXPLORE_SERVICE_URL}/api/adapters/{request.cloud_adapter_id}"
        )
        if meta_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cloud adapter not found"
            )
        meta_data = meta_resp.json().get("data", {})

    # Check for duplicate style name before creating
    name_check = await db.execute(select(Style).where(Style.name == request.style_name))
    if name_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"本地已存在名为 '{request.style_name}' 的风格，请修改名称后重试"
        )

    new_style = Style(
        name=request.style_name,
        description=request.description or meta_data.get("description"),
        target_style=request.style_tag,
        base_model=request.base_model or meta_data.get("base_model", "llama-2-3b"),
        status="available",
        source="explored",
    )
    db.add(new_style)
    await db.commit()
    await db.refresh(new_style)

    style_id = str(new_style.id)
    adapter_dir = Path(settings.MODELS_DIR) / "adapters" / style_id

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            download_resp = await client.get(
                f"{EXPLORE_SERVICE_URL}/api/adapters/{request.cloud_adapter_id}/download",
                follow_redirects=True,
            )
            if download_resp.status_code != 200:
                await db.delete(new_style)
                await db.commit()
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to download adapter from cloud"
                )

            temp_zip_path = adapter_dir.with_suffix(".zip")
            temp_zip_path.parent.mkdir(parents=True, exist_ok=True)
            temp_zip_path.write_bytes(download_resp.content)

        adapter_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(temp_zip_path, "r") as zf:
            zf.extractall(adapter_dir)

        temp_zip_path.unlink(missing_ok=True)

        adapter_path = str(Path(settings.MODELS_DIR) / "adapters" / style_id)
        new_style.adapter_path = adapter_path
        await db.commit()
        await db.refresh(new_style)

        # Create corresponding Task record with COMPLETED status
        task = Task(
            style_id=new_style.id,
            name=new_style.name,
            status="COMPLETED",
            progress=100,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        # Create Evaluation record if evaluation_results provided
        if request.evaluation_results:
            eval_data = request.evaluation_results
            evaluation = Evaluation(
                task_id=task.id,
                style_id=new_style.id,
                task_name=new_style.name,
                target_style=new_style.target_style,
                overall_score=eval_data.overall_score,
                sample_count=eval_data.sample_count,
                char_retention=eval_data.char_retention,
                style_score=eval_data.style_score,
                fluency_score=eval_data.fluency_score,
                vocab_diversity=eval_data.vocab_diversity,
                length_ratio=eval_data.length_ratio,
                bleu_score=eval_data.bleu_score,
                bert_score=eval_data.bert_score,
                avg_response_time=eval_data.avg_response_time,
                samples=json.dumps(eval_data.samples, ensure_ascii=False) if eval_data.samples else None,
                comment=eval_data.comment,
            )
            db.add(evaluation)
            await db.commit()

    except Exception as e:
        await db.delete(new_style)
        await db.commit()
        if adapter_dir.exists():
            shutil.rmtree(adapter_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import adapter: {str(e)}"
        )

    return PullAdapterResponse(
        id=style_id,
        name=new_style.name,
        target_style=new_style.target_style,
        description=new_style.description,
        base_model=new_style.base_model,
        adapter_path=new_style.adapter_path,
        status=new_style.status,
        source=new_style.source,
        created_at=new_style.created_at.isoformat() if new_style.created_at else "",
    )


@router.post("/upload-to-cloud")
async def upload_local_adapter_to_cloud(
    style_id: str,
    cloud_token: str,
    description: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Pack local adapter and upload directly to explore cloud service."""
    # Step 1: Validate local style
    result = await db.execute(select(Style).where(Style.id == style_id))
    style = result.scalar_one_or_none()

    if not style:
        raise HTTPException(status_code=404, detail="Style not found")

    if style.status not in ("available", "completed"):
        raise HTTPException(
            status_code=400,
            detail=f"Style status is '{style.status}', must be 'available' or 'completed'"
        )

    if not style.adapter_path:
        raise HTTPException(status_code=400, detail="Style has no adapter path")

    # Step 2: Find latest evaluation
    eval_result = await db.execute(
        select(Evaluation)
        .where(Evaluation.style_id == style_id)
        .order_by(Evaluation.created_at.desc())
    )
    evaluation = eval_result.scalar_one_or_none()
    eval_dict = _get_evaluation_dict(evaluation)

    # Step 3: Pack adapter to zip
    zip_path = None
    try:
        zip_path = _pack_adapter_to_zip(style.adapter_path)
        zip_size = os.path.getsize(zip_path)

        # Step 4: Upload to cloud
        async with httpx.AsyncClient(timeout=300.0) as client:
            with open(zip_path, "rb") as f:
                files = {"file": (f"{style.name}.zip", f, "application/zip")}
                data = {
                    "style_name": style.name,
                    "style_tag": style.target_style,
                    "description": description or style.description or "",
                    "base_model": style.base_model,
                    "local_style_id": str(style.id),
                }
                if eval_dict:
                    data["evaluation_results"] = json.dumps(eval_dict, ensure_ascii=False)

                resp = await client.post(
                    f"{EXPLORE_SERVICE_URL}/api/adapters",
                    data=data,
                    files=files,
                    headers={"Authorization": f"Bearer {cloud_token}"},
                )

            if resp.status_code not in (200, 201):
                detail = resp.json().get("detail", "Upload failed")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Cloud upload failed: {detail}"
                )

        return resp.json()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload adapter: {str(e)}"
        )
    finally:
        if zip_path and os.path.exists(zip_path):
            os.remove(zip_path)
