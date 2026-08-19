import { moeda } from '../formato'

/**
 * Barras horizontais de série única — a forma certa para "magnitude ordenada".
 *
 * Série única não leva legenda: o título do card já nomeia a medida. Cada barra
 * é rotulada diretamente, então a cor não carrega informação nenhuma e o
 * gráfico continua legível em preto e branco ou com daltonismo.
 */
export default function BarList({ dados, vazio = 'Sem dados no período.' }) {
  if (!dados.length) return <p className="empty">{vazio}</p>

  // Escala relativa ao maior valor: a barra maior sempre preenche a faixa.
  const maximo = Math.max(...dados.map((d) => d.valor)) || 1

  return (
    <div className="bars">
      {dados.map((d) => {
        const pct = (d.valor / maximo) * 100
        return (
          <div className="bar-row" key={d.chave}>
            <span className="bar-name" title={d.nome}>
              {d.nome}
            </span>
            <span className="bar-value">
              {moeda(d.valor)}
              {d.detalhe ? <span className="datas"> · {d.detalhe}</span> : null}
            </span>
            <div
              className="bar-track"
              role="img"
              aria-label={`${d.nome}: ${moeda(d.valor)}`}
            >
              <div className="bar-fill" style={{ width: `${pct}%` }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}
