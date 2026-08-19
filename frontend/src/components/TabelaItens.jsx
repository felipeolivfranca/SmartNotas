import { useMemo, useState } from 'react'
import { moeda, quantidade, dataCurta, rotuloCategoria } from '../formato'

const COLUNAS = [
  { chave: 'nome', rotulo: 'Produto', numerico: false },
  { chave: 'categoria', rotulo: 'Categoria', numerico: false },
  { chave: 'quantidade', rotulo: 'Qtd', numerico: true },
  { chave: 'ocorrencias', rotulo: 'Compras', numerico: true },
  { chave: 'preco_medio', rotulo: 'Preço médio', numerico: true },
  { chave: 'valor_total', rotulo: 'Total gasto', numerico: true },
]

export default function TabelaItens({ itens, onEditar }) {
  const [busca, setBusca] = useState('')
  const [ordem, setOrdem] = useState({ chave: 'valor_total', desc: true })

  const visiveis = useMemo(() => {
    const termo = busca.trim().toLowerCase()
    const filtrados = termo
      ? itens.filter(
          (i) =>
            i.nome.toLowerCase().includes(termo) ||
            rotuloCategoria(i.categoria).toLowerCase().includes(termo),
        )
      : itens

    const copia = [...filtrados]
    copia.sort((a, b) => {
      const x = a[ordem.chave]
      const y = b[ordem.chave]
      // Campos numéricos podem vir null (preço médio sem quantidade); eles vão
      // para o fim independente da direção, para não poluir o topo da tabela.
      if (x == null && y == null) return 0
      if (x == null) return 1
      if (y == null) return -1
      const cmp = typeof x === 'string' ? x.localeCompare(y, 'pt-BR') : x - y
      return ordem.desc ? -cmp : cmp
    })
    return copia
  }, [itens, busca, ordem])

  const maximo = Math.max(...itens.map((i) => i.valor_total), 0) || 1
  const totalVisivel = visiveis.reduce((soma, i) => soma + i.valor_total, 0)

  function alternar(chave) {
    setOrdem((atual) =>
      atual.chave === chave
        ? { chave, desc: !atual.desc }
        // Texto começa em A→Z; número começa do maior, que é o que interessa.
        : { chave, desc: chave !== 'nome' && chave !== 'categoria' },
    )
  }

  if (!itens.length) {
    return (
      <p className="empty">
        Nenhum item neste período. Envie a foto de uma nota fiscal para começar.
      </p>
    )
  }

  return (
    <>
      <div style={{ marginBottom: 14 }}>
        <input
          className="input"
          type="search"
          placeholder="Filtrar por produto ou categoria…"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          aria-label="Filtrar itens"
        />
      </div>

      <div className="table-wrap">
        <table>
          <caption className="sr-only">
            Itens somados no período, agrupados por produto e unidade
          </caption>
          <thead>
            <tr>
              {COLUNAS.map((coluna) => {
                const ativa = ordem.chave === coluna.chave
                return (
                  <th
                    key={coluna.chave}
                    className={`sortable${coluna.numerico ? ' num' : ''}`}
                    onClick={() => alternar(coluna.chave)}
                    aria-sort={ativa ? (ordem.desc ? 'descending' : 'ascending') : 'none'}
                  >
                    {coluna.rotulo}
                    {ativa ? (ordem.desc ? ' ↓' : ' ↑') : ''}
                  </th>
                )
              })}
              <th>Datas</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            {visiveis.map((item) => (
              <tr key={item.chave}>
                <td>
                  <div className="produto">
                    <div
                      className="mini-track"
                      title={`${((item.valor_total / maximo) * 100).toFixed(0)}% do maior gasto`}
                    >
                      <div
                        className="mini-fill"
                        style={{ width: `${(item.valor_total / maximo) * 100}%` }}
                      />
                    </div>
                    <span className="produto-nome">{item.nome}</span>
                  </div>
                </td>
                <td>
                  <span className="chip">{rotuloCategoria(item.categoria)}</span>
                </td>
                <td className="num">
                  {quantidade(item.quantidade)}{' '}
                  <span className="chip chip-unidade">{item.unidade}</span>
                </td>
                <td className="num">{item.ocorrencias}x</td>
                <td className="num">
                  {item.preco_medio == null ? '—' : moeda(item.preco_medio)}
                  {item.preco_min != null &&
                  item.preco_max != null &&
                  item.preco_max - item.preco_min > 0.01 ? (
                    <div className="datas">
                      {moeda(item.preco_min)}–{moeda(item.preco_max)}
                    </div>
                  ) : null}
                </td>
                <td className="num">
                  <strong>{moeda(item.valor_total)}</strong>
                </td>
                <td className="datas">{item.datas.map(dataCurta).join(', ')}</td>
                <td>
                  {onEditar ? (
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => onEditar(item)}
                      title="Corrigir o nome usado no agrupamento"
                    >
                      Corrigir
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>

          <tfoot>
            <tr>
              <td colSpan={5} style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                {visiveis.length} de {itens.length} produtos
              </td>
              <td className="num">
                <strong>{moeda(totalVisivel)}</strong>
              </td>
              <td colSpan={2}></td>
            </tr>
          </tfoot>
        </table>
      </div>
    </>
  )
}
