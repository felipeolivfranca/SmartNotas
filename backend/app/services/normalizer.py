"""Normalização de nomes de produto — a chave que faz o agrupamento funcionar.

A IA já devolve um `nome_canonico` genérico ("requeijão"), mas ela pode variar
acento, caixa e plural entre notas. Esta camada colapsa essas variações para
que "Requeijão", "requeijao" e "requeijões" caiam no mesmo grupo.
"""

from __future__ import annotations

import re
import unicodedata

# Plurais irregulares comuns em rótulo de supermercado, onde só cortar o "s"
# final produziria a palavra errada.
_PLURAIS_IRREGULARES = {
    "poes": "pao",
    "paes": "pao",
    "feijoes": "feijao",
    "requeijoes": "requeijao",
    "limoes": "limao",
    "mamoes": "mamao",
    "meloes": "melao",
    "botoes": "botao",
    "colheres": "colher",
    "ovos": "ovo",
    "arrozes": "arroz",
    "cervejas": "cerveja",
}

_SUFIXOS_PLURAL = ("oes", "aes", "ais", "eis", "ns", "es", "s")


def remover_acentos(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def _singularizar(palavra: str) -> str:
    if len(palavra) <= 3:
        return palavra
    if palavra in _PLURAIS_IRREGULARES:
        return _PLURAIS_IRREGULARES[palavra]
    for sufixo in _SUFIXOS_PLURAL:
        if palavra.endswith(sufixo) and len(palavra) - len(sufixo) >= 3:
            base = palavra[: -len(sufixo)]
            if sufixo in ("oes", "aes"):
                return base + "ao"
            if sufixo in ("ais", "eis"):
                return base + "l"
            return base
    return palavra


def normalizar_nome(nome: str) -> str:
    """Reduz um nome de produto à sua chave de agrupamento.

    >>> normalizar_nome("Requeijão Cremoso")
    'requeijao cremoso'
    >>> normalizar_nome("REQUEIJÕES")
    'requeijao'
    """
    texto = remover_acentos(nome).lower()
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    palavras = [_singularizar(p) for p in texto.split() if p]
    return " ".join(palavras)
