"""Versioning endpoints for datasets and models."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.data_pipeline.config import get_config
from backend.data_pipeline.storage import ParquetStorage
from backend.services.version_registry import version_registry

router = APIRouter(prefix="/api/versioning", tags=["versioning"])
storage = ParquetStorage(get_config())


@router.get("/datasets")
async def list_dataset_runs(
    symbol: str,
    timeframe: str,
    layer: str = "silver",
    dataset_version: Optional[str] = None,
):
    runs = storage.list_runs(layer, symbol, timeframe, dataset_version)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "layer": layer,
        "dataset_version": dataset_version or storage._config.dataset_namespace,
        "runs": runs,
    }


class ActivateDatasetRequest(BaseModel):
    symbol: str
    timeframe: str
    dataset_version: str
    run_id: str


@router.post("/datasets/activate")
async def activate_dataset_version(request: ActivateDatasetRequest):
    runs = storage.list_runs("silver", request.symbol, request.timeframe, request.dataset_version)
    if request.run_id not in runs:
        raise HTTPException(status_code=404, detail="Run ID not found for dataset")

    version_registry.set_dataset_override(
        symbol=request.symbol,
        timeframe=request.timeframe,
        dataset_version=request.dataset_version,
        run_id=request.run_id,
    )
    return {"status": "activated", "symbol": request.symbol, "timeframe": request.timeframe}


@router.delete("/datasets/activate")
async def clear_dataset_activation(symbol: str, timeframe: str):
    version_registry.clear_dataset_override(symbol, timeframe)
    return {"status": "cleared", "symbol": symbol, "timeframe": timeframe}


@router.get("/datasets/active")
async def list_active_overrides():
    return version_registry.list_dataset_overrides()


