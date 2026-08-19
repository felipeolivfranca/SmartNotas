"""Schema que a IA é obrigada a devolver (structured outputs).

Os enums existem para o agrupamento não depender da IA inventar uma grafia
nova de unidade ou categoria a cada nota.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Unidade(str, Enum):
    UN = "UN"
    KG = "KG"
    G = "G"
    L = "L"
    ML = "ML"
    DZ = "DZ"
    PCT = "PCT"


class Categoria(str, Enum):
    laticinios = "laticinios"
    carnes = "carnes"
    frutas_verduras = "frutas_verduras"
    padaria = "padaria"
    mercearia = "mercearia"
    bebidas = "bebidas"
    congelados = "congelados"
    limpeza = "limpeza"
    higiene = "higiene"
    pet = "pet"
    outros = "outros"


class ItemExtraido(BaseModel):
    descricao_original: str = Field(
        description="A descrição exatamente como aparece impressa na nota, incluindo abreviações."
    )
    nome_canonico: str = Field(
        description=(
            "Nome genérico do produto em português, minúsculo e no singular, "
            "SEM marca, SEM peso/volume e SEM embalagem. "
            "Ex.: 'REQ CREMOSO TIROL 200G' -> 'requeijão'; "
            "'LEITE INT ITALAC 1L' -> 'leite integral'."
        )
    )
    categoria: Categoria
    quantidade: float = Field(description="Quantidade comprada deste item nesta nota.")
    unidade: Unidade
    valor_unitario: float | None = Field(
        default=None, description="Preço de uma unidade. null se a nota não mostrar."
    )
    valor_total: float = Field(description="Valor total pago neste item (quantidade x unitário).")


class NotaExtraida(BaseModel):
    estabelecimento: str | None = Field(default=None, description="Nome da loja/mercado.")
    cnpj: str | None = None
    data_compra: str | None = Field(
        default=None, description="Data da compra no formato AAAA-MM-DD. null se ilegível."
    )
    total_informado: float | None = Field(
        default=None, description="O valor TOTAL impresso na nota, se visível."
    )
    itens: list[ItemExtraido]
    observacao: str | None = Field(
        default=None,
        description=(
            "Preencha somente se algo impediu a leitura completa: trecho cortado, "
            "borrado ou ilegível. Caso contrário, null."
        ),
    )
