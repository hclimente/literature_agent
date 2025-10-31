from datetime import date
import re

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    HttpUrl,
    TypeAdapter,
)

from .utils import get_common_variations


class Author(BaseModel):
    """Model representing an author of a scientific article."""

    first_name: str
    last_name: str


class InstitutionalAuthor(BaseModel):
    """Model representing an institutional author of a scientific article."""

    name: str


class Article(BaseModel):
    """Model representing a scientific article with metadata and processing results."""

    # Core metadata fields
    title: str | None = None
    authors: list[Author | InstitutionalAuthor] | None = None
    summary: str | None = None
    doi: str | None = None
    url: HttpUrl

    # Publication information
    journal_name: str
    journal_short_name: str | None = None
    volume: int | None = None
    issue: int | None = None
    date: date

    # Other metadata
    language: str | None = None

    # LLM results
    screening_decision: bool | None = None
    screening_reasoning: str | None = None

    priority_decision: str | None = None
    priority_reasoning: str | None = None

    # Raw and integration data
    access_date: date
    raw_contents: str
    zotero_key: str | None = None


ArticleList = TypeAdapter(list[Article])


class MetadataResponse(BaseModel):
    """Model for LLM response containing article metadata."""

    title: str
    summary: str
    url: HttpUrl
    doi: str

    @field_validator("doi", mode="after")
    @classmethod
    def is_valid_doi(cls, doi: str) -> bool:
        if not re.match(r"^10\.\d{4,}/[^\s]+$", doi):
            raise ValueError(f"Invalid DOI format: {doi}")
        return doi


class ScreeningResponse(BaseModel):
    """Model for LLM response containing article screening results."""

    doi: str
    screening_decision: bool = Field(validation_alias="decision")
    screening_reasoning: str = Field(validation_alias="reasoning")

    @field_validator("screening_decision", mode="before")
    @classmethod
    def clean_response(cls, decision: str) -> str:
        if type(decision) is bool:
            return decision

        mapping = get_common_variations(["true", "false"])
        return mapping[decision.lower()]


class PriorityResponse(BaseModel):
    """Model for LLM response containing article priority assessment."""

    doi: str
    priority_decision: str = Field(validation_alias="decision")
    priority_reasoning: str = Field(validation_alias="reasoning")

    @field_validator("priority_decision", mode="before")
    @classmethod
    def clean_response(cls, decision: str) -> str:
        mapping = get_common_variations(["high", "medium", "low"])
        return mapping[decision.lower()]


def pprint(model: BaseModel, exclude_none: bool = True) -> str:
    """
    Pretty print a Pydantic model, list, or dict of models as JSON.

    Args:
        model (BaseModel): The Pydantic model, list, or dict to print.
        exclude_none (bool): Whether to exclude None values from output.

    Returns:
        str: JSON string representation of the model.
    """
    if isinstance(model, BaseModel):
        return model.model_dump_json(indent=2, exclude_none=exclude_none)
    elif isinstance(model, list):
        output = "[\n"
        for i, item in enumerate(model):
            output += item.model_dump_json(indent=2, exclude_none=exclude_none)
            if i < len(model) - 1:
                output += ","
            output += "\n"
        output += "]"
        return output
    elif isinstance(model, dict):
        output = "{\n"
        items = list(model.items())
        for i, (key, item) in enumerate(items):
            output += f'"{key}": ' + item.model_dump_json(
                indent=2, exclude_none=exclude_none
            )
            if i < len(items) - 1:
                output += ","
            output += "\n"
        output += "}"
        return output
    else:
        raise TypeError(
            "Input must be a Pydantic BaseModel, a list or a dict of BaseModels."
        )
