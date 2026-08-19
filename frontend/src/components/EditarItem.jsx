import { useState } from 'react'
import { api } from '../api'
import { CATEGORIAS, rotuloCategoria } from '../formato'

/**
 * Correção manual de um grupo de produtos.
 *
 * O caso real: a IA leu "requeijao cremoso" numa nota e "requeijão" noutra, e
 * o dashboard mostrou dois grupos. Renomear aqui reescreve TODAS as linhas do
 * grupo, então ele passa a somar junto com o nome escolhido.
 */
export default function EditarItem({ item, onFechar, onSalvo }) {
  const [nome, setNome] = useState(item.nome)
  const [categoria, setCategoria] = useState(item.categoria)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)

  const inalterado = nome.trim() === item.nome && categoria === item.categoria

  async function salvar(evento) {
    evento.preventDefault()
    if (!nome.trim()) {
      setErro('O nome não pode ficar vazio.')
      return
    }

    setSalvando(true)
    setErro(null)
    try {
      await Promise.all(
        item.ids.map((id) =>
          api.atualizarItem(id, { nome_canonico: nome.trim(), categoria }),
        ),
      )
      onSalvo?.()
      onFechar()
    } catch (e) {
      setErro(e.message)
      setSalvando(false)
    }
  }

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onFechar()
      }}
    >
      <div className="modal" role="dialog" aria-modal="true" aria-label="Corrigir produto">
        <h2 style={{ marginBottom: 4 }}>Corrigir produto</h2>
        <p className="card-sub">
          {item.ids.length === 1
            ? 'Vale para a linha que hoje cai neste grupo.'
            : `Vale para as ${item.ids.length} linhas que hoje caem neste grupo.`}
        </p>

        <form onSubmit={salvar}>
          <div className="field">
            <label htmlFor="nome">Nome do produto</label>
            <input
              id="nome"
              className="input"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              autoFocus
            />
            <div className="field-hint">
              Use o nome genérico, no singular e sem marca — é ele que junta a mesma
              compra feita em datas diferentes. Digitar um nome que já existe funde os
              dois grupos.
            </div>
          </div>

          <div className="field">
            <label htmlFor="categoria">Categoria</label>
            <select
              id="categoria"
              className="select"
              style={{ width: '100%' }}
              value={categoria}
              onChange={(e) => setCategoria(e.target.value)}
            >
              {Object.keys(CATEGORIAS).map((chave) => (
                <option key={chave} value={chave}>
                  {rotuloCategoria(chave)}
                </option>
              ))}
            </select>
          </div>

          {erro ? (
            <div className="banner banner-critical" style={{ marginBottom: 0 }}>
              <span>⚠</span>
              <span>{erro}</span>
            </div>
          ) : null}

          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onFechar}>
              Cancelar
            </button>
            <button type="submit" className="btn" disabled={salvando || inalterado}>
              {salvando ? <span className="spinner" /> : null}
              {salvando ? 'Salvando…' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
