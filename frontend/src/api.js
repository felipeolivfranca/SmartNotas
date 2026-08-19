// Cliente da API. O Vite faz proxy de /api para o backend em 127.0.0.1:8000,
// então não há host hardcoded aqui.

async function pedir(url, options = {}) {
  const resposta = await fetch(url, options)

  if (!resposta.ok) {
    // FastAPI devolve o motivo em `detail`; sem isso a UI mostraria só "500".
    let detalhe = `HTTP ${resposta.status}`
    try {
      const corpo = await resposta.json()
      if (corpo?.detail) {
        detalhe = typeof corpo.detail === 'string' ? corpo.detail : JSON.stringify(corpo.detail)
      }
    } catch {
      /* resposta sem corpo JSON — fica o status */
    }
    throw new Error(detalhe)
  }

  return resposta.status === 204 ? null : resposta.json()
}

export const api = {
  health: () => pedir('/api/health'),

  meses: () => pedir('/api/dashboard/meses'),

  resumo: (mes) => pedir(`/api/dashboard/resumo${mes ? `?mes=${mes}` : ''}`),

  notas: () => pedir('/api/notas'),

  nota: (id) => pedir(`/api/notas/${id}`),

  excluirNota: (id) => pedir(`/api/notas/${id}`, { method: 'DELETE' }),

  atualizarItem: (id, alteracao) =>
    pedir(`/api/itens/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(alteracao),
    }),

  upload: (arquivos) => {
    const dados = new FormData()
    for (const arquivo of arquivos) dados.append('arquivos', arquivo)
    return pedir('/api/notas/upload', { method: 'POST', body: dados })
  },
}
