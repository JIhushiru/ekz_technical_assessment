from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar("T")


class StandardResponse(BaseModel, Generic[T]):
    status: str
    code: int
    message: str
    data: List[T]
