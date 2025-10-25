import re

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    HttpUrl,
    TypeAdapter,
)


class Article(BaseModel):
    title: str | None = None
    summary: str | None = None
    doi: str | None = None
    journal_name: str
    date: str
    url: str | HttpUrl
    # authors: list[Author]
    screening_decision: bool | None = None
    screening_reasoning: str | None = None
    priority_decision: int | None = None
    priority_reasoning: str | None = None
    raw_contents: str


ArticleList = TypeAdapter(list[Article])


class MetadataResponse(BaseModel):
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
    doi: str
    priority_decision: str = Field(validation_alias="decision")
    priority_reasoning: str = Field(validation_alias="reasoning")

    @field_validator("priority_decision", mode="before")
    @classmethod
    def clean_response(cls, decision: str) -> str:
        mapping = get_common_variations(["high", "medium", "low"])
        return mapping[decision.lower()]


def get_common_variations(expected_values: list):
    """
    Generate common variations of expected values (case, quotes, punctuation).

    Args:
        expected_values (list): List of expected values.

    Returns:
        dict: Mapping of variations to normalized values.
    """
    d = {}

    for v in expected_values:
        d[v] = v
        d[v.lower()] = v
        d[v.upper()] = v
        d[v.capitalize()] = v
        d[v.title()] = v

    update = {}
    for k, v in d.items():
        update[f"'{k}'"] = v
        update[f'"{k}"'] = v
        update[f"{k}."] = v

    d.update(update)
    return d


def pprint(model: BaseModel, exclude_none: bool = True) -> str:
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
