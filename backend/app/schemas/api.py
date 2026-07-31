from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

DataT = TypeVar("DataT")


class ApiSuccess(BaseModel, Generic[DataT]):
    """Standard envelope for successful API responses."""

    success: Literal[True] = True
    data: DataT


class ApiErrorDetail(BaseModel):
    code: str
    message: str


class ApiError(BaseModel):
    """Standard envelope for safe API error responses."""

    success: Literal[False] = False
    error: ApiErrorDetail
