import { moeda, periodoLongo } from '../formato'

export default function Tiles({ resumo }) {
  const maior = resumo.maior_gasto

  return (
    <div className="tiles">
      <div className="tile">
        <div className="tile-label">Gasto no mês</div>
        <div className="tile-value">{moeda(resumo.total_gasto)}</div>
        <div className="tile-hint">{periodoLongo(resumo.periodo)}</div>
      </div>

      <div className="tile">
        <div className="tile-label">Produtos distintos</div>
        <div className="tile-value">{resumo.produtos_distintos}</div>
        <div className="tile-hint">
          {resumo.total_itens} {resumo.total_itens === 1 ? 'linha lida' : 'linhas lidas'}
        </div>
      </div>

      <div className="tile">
        <div className="tile-label">Notas enviadas</div>
        <div className="tile-value">{resumo.total_notas}</div>
        <div className="tile-hint">no período</div>
      </div>

      <div className="tile">
        <div className="tile-label">Maior gasto</div>
        <div className="tile-value tile-produto" style={{ fontSize: '1.15rem' }}>
          {maior ? maior.nome : '—'}
        </div>
        <div className="tile-hint">
          {maior ? `${moeda(maior.valor_total)} em ${maior.ocorrencias}x` : 'sem dados'}
        </div>
      </div>
    </div>
  )
}
