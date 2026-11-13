import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Texto em português por tipo de erro do pydantic; {…} vem do "ctx" do erro (ex.: o limite que foi passado).
MESSAGES = {
    "missing": "campo obrigatório",
    "string_type": "deve ser um texto",
    "int_type": "deve ser um número inteiro",
    "int_parsing": "deve ser um número inteiro",
    "float_type": "deve ser um número",
    "float_parsing": "deve ser um número",
    "bool_type": "deve ser verdadeiro ou falso",
    "bool_parsing": "deve ser verdadeiro ou falso",
    "enum": "valor fora da lista permitida ({expected})",
    "literal_error": "valor fora da lista permitida ({expected})",
    "datetime_type": "deve ser uma data e hora (ex.: 2026-11-13T15:00:00Z)",
    "datetime_parsing": "deve ser uma data e hora (ex.: 2026-11-13T15:00:00Z)",
    "datetime_from_date_parsing": "deve ser uma data e hora (ex.: 2026-11-13T15:00:00Z)",
    "too_short": "curto demais (mínimo {min_length})",
    "too_long": "grande demais (máximo {max_length})",
    "string_too_short": "curto demais (mínimo {min_length})",
    "string_too_long": "grande demais (máximo {max_length})",
    "greater_than": "deve ser maior que {gt}",
    "greater_than_equal": "deve ser no mínimo {ge}",
    "less_than": "deve ser menor que {lt}",
    "less_than_equal": "deve ser no máximo {le}",
    "finite_number": "deve ser um número finito",
    "model_type": "formato inválido",
    "dict_type": "formato inválido",
    "list_type": "deve ser uma lista",
}
HTTP_MESSAGES = {
    404: "Endereço não encontrado. Confira a URL na documentação (/docs).",
    405: "Método não permitido neste endereço. Confira a documentação (/docs).",
}


def describe(error: dict) -> str:
    """Uma frase em português para um erro de validação do pydantic."""
    if error["type"] == "json_invalid":
        return "o corpo não é um JSON válido"
    field = ".".join(str(part) for part in error["loc"][1:]) or "corpo"
    template = MESSAGES.get(error["type"], "valor inválido")
    try:
        text = template.format(**error.get("ctx", {}))
    except (KeyError, IndexError):
        text = template
    return f"{field}: {text}"


async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Nunca devolvemos o "input" do erro: ele pode trazer o valor enviado (e NaN quebra o JSON).
    problems = "; ".join(describe(error) for error in exc.errors()[:3])
    return JSONResponse(status_code=422, content={"detail": f"Dados inválidos ({problems}). Corrija e envie de novo."})


async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    try:
        default = HTTPStatus(exc.status_code).phrase
    except ValueError:  # código fora da enumeração (ex.: 499): não há frase padrão para trocar
        default = None
    detail = HTTP_MESSAGES.get(exc.status_code, exc.detail) if exc.detail == default else exc.detail
    return JSONResponse(status_code=exc.status_code, content={"detail": detail}, headers=exc.headers)


async def unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    logging.getLogger("geraldo.errors").exception("erro inesperado", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor. Tente de novo; se persistir, avise o suporte."})


def install(app: FastAPI) -> None:
    """Todo erro do backend sai como {"detail": "<o que houve + o que fazer>"} (schema Error do contrato)."""
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(StarletteHTTPException, http_error)
    app.add_exception_handler(Exception, unexpected_error)
