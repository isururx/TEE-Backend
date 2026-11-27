from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AnalyticsPeriod(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    timezone: str = "UTC"


class AnalyticsSummary(BaseModel):
    total_detections: int
    diseased_detections: int
    healthy_detections: int
    unassigned_detections: int


class DiseaseFrequencyItem(BaseModel):
    disease_id: Optional[int] = None
    disease_name: str
    frequency: int


class BlockDiseaseFrequency(BaseModel):
    block_id: int
    block_name: str
    total_detections: int
    diseases: list[DiseaseFrequencyItem]


class DiseaseFrequencyByBlockResponse(BaseModel):
    period: AnalyticsPeriod
    summary: AnalyticsSummary
    blocks: list[BlockDiseaseFrequency]
    filters: dict


class DiseaseDistributionResponse(BaseModel):
    period: AnalyticsPeriod
    total_detections: int
    diseased_detections: int
    disease_distribution: list[DiseaseFrequencyItem]
    filters: dict


class BlockDiseaseSummary(BaseModel):
    block_id: int
    block_name: str
    total_detections: int
    healthy_detections: int
    diseased_detections: int
    diseases: list[DiseaseFrequencyItem]
    most_frequently_detected_diseases: list[str]


class BlockDiseaseSummaryResponse(BaseModel):
    period: AnalyticsPeriod
    summary: AnalyticsSummary
    block: BlockDiseaseSummary
    filters: dict
