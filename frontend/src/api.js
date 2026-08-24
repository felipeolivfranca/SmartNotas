// Cliente da API. O Vite faz proxy de /api para o backend em 127.0.0.1:8000,
// então não há host hardcoded aqui.

async function pedir(url, options = {}) {
  const resposta = await fetch(url, {
    // O login vive num cookie httpOnly; sem isto ele não acompanharia a
    // chamada e toda rota protegida responderia 401.
    credentials: 'include',
    ...options,
  })

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
    const erro = new Error(detalhe)
    // Quem chama precisa distinguir "sessão acabou" de "deu erro": o 401 leva
    // de volta para a tela de login, o resto vira banner de erro.
    erro.status = resposta.status
    throw erro
  }

  return resposta.status === 204 ? null : resposta.json()
}

function enviarJson(url, corpo) {
  return pedir(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(corpo),
  })
}

export const api = {
  health: () => pedir('/api/health'),

  eu: () => pedir('/api/auth/eu'),

  login: (email, senha) => enviarJson('/api/auth/login', { email, senha }),

  registrar: (nome, email, senha) => enviarJson('/api/auth/registrar', { nome, email, senha }),

  logout: () => pedir('/api/auth/logout', { method: 'POST' }),

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
