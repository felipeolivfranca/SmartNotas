import { useState } from 'react'
import { api } from '../api'
import { moeda, dataCurta } from '../formato'

export default function ListaNotas({ notas, onMudou }) {
  const [excluindo, setExcluindo] = useState(null)

  async function excluir(nota) {
    // Sem window.confirm: a exclusão é reversível reenviando a foto, e um
    // modal bloqueante aqui atrapalharia mais do que protegeria.
    setExcluindo(nota.id)
    try {
      await api.excluirNota(nota.id)
      onMudou?.()
    } finally {
      setExcluindo(null)
    }
  }

  if (!notas.length) {
    return <p className="empty">Nenhuma nota enviada ainda.</p>
  }

  return (
    <ul className="notas">
      {notas.map((nota) => {
        // Diferença entre o total impresso e a soma dos itens: é o sinal de
        // que a IA perdeu alguma linha da foto.
        const divergencia =
          nota.total_informado != null && nota.total_calculado != null
            ? nota.total_informado - nota.total_calculado
            : null

        return (
          <li className="nota" key={nota.id}>
            <div className="nota-main">
              <div className="nota-loja">{nota.estabelecimento || nota.arquivo_nome}</div>
              <div className="nota-meta">
                {dataCurta(nota.data_compra)} · {nota.qtd_itens}{' '}
                {nota.qtd_itens === 1 ? 'item' : 'itens'} · {moeda(nota.total_calculado)}
              </div>
              {divergencia != null && Math.abs(divergencia) > 0.05 ? (
                <div className="divergencia">
                  Total impresso {moeda(nota.total_informado)} — diferença de{' '}
                  {moeda(Math.abs(divergencia))}, confira se algum item ficou de fora.
                </div>
              ) : null}
              {nota.erro_msg ? <div className="divergencia">{nota.erro_msg}</div> : null}
            </div>

            <a
              className="btn btn-ghost btn-sm"
              href={`/api/notas/${nota.id}/imagem`}
              target="_blank"
              rel="noreferrer"
            >
              Ver foto
            </a>

            <button
              className="link-danger"
              onClick={() => excluir(nota)}
              disabled={excluindo === nota.id}
            >
              {excluindo === nota.id ? 'Excluindo…' : 'Excluir'}
            </button>
          </li>
        )
      })}
    </ul>
  )
}
