"""Leitura da nota fiscal com Gemini (visão + structured outputs)."""

from __future__ import annotations

import io
import logging

from google import genai
from google.genai import errors, types
from PIL import Image

from ..config import settings
from .schemas import NotaExtraida

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Você extrai dados de notas fiscais e cupons fiscais brasileiros (NFC-e, NF-e, \
cupom de supermercado) a partir de fotos.

Regras de leitura:
- Transcreva TODOS os itens da nota, inclusive os que aparecem cortados no fim da \
  imagem, desde que a descrição e o valor sejam legíveis.
- Cupons brasileiros usam vírgula como separador decimal ("12,90"). Converta para \
  ponto decimal ("12.90").
- Linhas de desconto, troco, subtotal, taxa e forma de pagamento NÃO são itens. \
  Ignore-as.
- Se a nota mostrar quantidade e valor unitário, use-os. Se mostrar só o valor \
  total do item, use quantidade 1 e deixe valor_unitario null.
- Produtos vendidos a peso vêm com unidade KG e quantidade fracionária \
  (ex.: 0,436 KG de tomate).

O campo nome_canonico é o mais importante: ele é usado para somar o mesmo produto \
comprado em datas diferentes. Portanto ele deve ser o nome genérico do produto, \
minúsculo, no singular, sem marca, sem peso/volume e sem tipo de embalagem — de \
modo que a mesma compra feita em dias ou mercados diferentes caia no mesmo nome.

Exemplos:
  "REQ CREM TIROL 200G"      -> nome_canonico: "requeijão"
  "REQUEIJAO CREMOSO VIGOR"  -> nome_canonico: "requeijão"
  "LEITE INT ITALAC 1L"      -> nome_canonico: "leite integral"
  "BANANA PRATA KG"          -> nome_canonico: "banana"
  "SAB PO OMO 1,6KG"         -> nome_canonico: "sabão em pó"
  "COCA COLA 2L"             -> nome_canonico: "refrigerante"

Não invente dados. Qualquer campo ilegível deve vir null, e o motivo deve ir em \
observacao. É melhor devolver um campo null do que um valor adivinhado.\
"""

USER_PROMPT = (
    "Extraia todos os itens desta nota fiscal, seguindo as regras do sistema. "
    "Confira ao final se a soma dos valor_total dos itens está coerente com o "
    "total impresso na nota."
)

IMAGE_MEDIA_TYPES = {
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
    "image/webp": "image/webp",
    "image/gif": "image/gif",
}

# Motivos de parada que significam "não veio conteúdo utilizável", com a
# explicação que o usuário final consegue agir em cima.
FALHAS = {
    types.FinishReason.MAX_TOKENS: (
        "A nota é longa demais e a leitura foi truncada. Tente fotografar em partes."
    ),
    types.FinishReason.SAFETY: "O modelo bloqueou esta imagem por política de conteúdo.",
    types.FinishReason.PROHIBITED_CONTENT: (
        "O modelo bloqueou esta imagem por política de conteúdo."
    ),
    types.FinishReason.RECITATION: "O modelo interrompeu a leitura por política de citação.",
    types.FinishReason.BLOCKLIST: "O modelo bloqueou esta imagem por política de conteúdo.",
    types.FinishReason.SPII: "O modelo detectou dados sensíveis e interrompeu a leitura.",
}


class ExtracaoError(RuntimeError):
    """Falha na leitura da nota — mensagem já pronta para o usuário final."""


def _cliente() -> genai.Client:
    if not settings.gemini_api_key:
        raise ExtracaoError(
            "GEMINI_API_KEY não configurada. Copie backend/.env.example para "
            "backend/.env e preencha a chave gerada em aistudio.google.com/apikey."
        )
    return genai.Client(api_key=settings.gemini_api_key)


def preparar_imagem(conteudo: bytes) -> tuple[bytes, str]:
    """Reduz a imagem e devolve (bytes JPEG, media_type).

    Fotos de celular chegam com 4000px+ de largura. Acima do limite configurado
    o excedente vira custo de token sem ganho de OCR.
    """
    with Image.open(io.BytesIO(conteudo)) as img:
        img = img.convert("RGB")
        maior_lado = max(img.size)
        if maior_lado > settings.MAX_IMAGE_EDGE:
            fator = settings.MAX_IMAGE_EDGE / maior_lado
            novo = (max(1, int(img.width * fator)), max(1, int(img.height * fator)))
            img = img.resize(novo, Image.LANCZOS)

        buffer = io.BytesIO()
        # Qualidade alta: artefato de compressão em cupom desbotado custa item perdido.
        img.save(buffer, format="JPEG", quality=90, optimize=True)

    return buffer.getvalue(), "image/jpeg"


def _parte_documento(conteudo: bytes, content_type: str) -> types.Part:
    if content_type == "application/pdf":
        return types.Part.from_bytes(data=conteudo, mime_type="application/pdf")

    if content_type not in IMAGE_MEDIA_TYPES:
        raise ExtracaoError(
            f"Formato não suportado: {content_type}. Envie JPG, PNG, WEBP ou PDF."
        )

    dados, media_type = preparar_imagem(conteudo)
    return types.Part.from_bytes(data=dados, mime_type=media_type)


def extrair_nota(conteudo: bytes, content_type: str) -> tuple[NotaExtraida, str]:
    """Lê uma nota e devolve (dados extraídos, modelo usado)."""
    cliente = _cliente()
    modelo = settings.model
    parte = _parte_documento(conteudo, content_type)

    try:
        resposta = cliente.models.generate_content(
            model=modelo,
            # O documento vem antes do texto: é a ordem que o modelo lê melhor.
            contents=[parte, USER_PROMPT],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                # Structured output: o modelo é obrigado a devolver o schema.
                response_mime_type="application/json",
                response_schema=NotaExtraida,
                max_output_tokens=16000,
                # Cupom tem letra pequena e desbotada — resolução alta é o que
                # separa ler "R$ 8,50" de perder a linha inteira.
                media_resolution=types.MediaResolution.MEDIA_RESOLUTION_HIGH,
                # A leitura é transcrição, não criação: temperatura baixa reduz
                # o risco de o modelo "completar" um valor ilegível.
                temperature=0.0,
                # Não há ferramenta nenhuma aqui; desligar evita o aviso que o
                # SDK emite a cada chamada.
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            ),
        )
    except errors.ClientError as exc:
        logger.exception("Erro de requisição na API do Gemini")
        raise ExtracaoError(f"A API do Gemini recusou a requisição: {exc.message}") from exc
    except errors.ServerError as exc:
        logger.exception("Erro do servidor na API do Gemini")
        raise ExtracaoError(
            "A API do Gemini está indisponível no momento. Tente novamente em instantes."
        ) from exc
    except errors.APIError as exc:
        logger.exception("Erro inesperado da API do Gemini")
        raise ExtracaoError(f"Falha ao falar com a API do Gemini: {exc.message}") from exc

    # O prompt pode ser barrado antes mesmo de gerar um candidato.
    feedback = resposta.prompt_feedback
    if feedback is not None and feedback.block_reason is not None:
        raise ExtracaoError("O modelo bloqueou esta imagem por política de conteúdo.")

    if not resposta.candidates:
        raise ExtracaoError("O modelo não devolveu nenhuma leitura para esta imagem.")

    motivo = resposta.candidates[0].finish_reason
    if motivo in FALHAS:
        raise ExtracaoError(FALHAS[motivo])

    dados = resposta.parsed
    if not isinstance(dados, NotaExtraida):
        raise ExtracaoError("Não foi possível interpretar a resposta do modelo.")

    return dados, modelo
