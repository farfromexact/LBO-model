from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from lbo.schemas.standard_model import StandardModel


class AdapterMatch(BaseModel):
    adapter_name: str
    confidence: float = Field(ge=0, le=1)
    can_handle: bool
    detected_template: str = "Unknown"
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class BaseWorkbookAdapter(ABC):
    adapter_name: str

    @abstractmethod
    def can_handle(self, workbook) -> AdapterMatch:
        raise NotImplementedError

    @abstractmethod
    def extract(self, workbook) -> StandardModel:
        raise NotImplementedError

