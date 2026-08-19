import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import { moeda, periodoAtual, periodoLongo, rotuloCategoria } from './formato'
import BarList from './components/BarList'
import EditarItem from './components/EditarItem'
import ListaNotas from './components/ListaNotas'
import TabelaItens from './components/TabelaItens'
import Tiles from './components/Tiles'
import Upload from './components/Upload'

const TOP_N = 8

export default function App() {
  const [mes, setMes] = useState(periodoAtual())
  const [meses, setMeses] = useState([])
  const [resumo, setResumo] = useState(null)
  const [notas, setNotas] = useState([])
  const [saude, setSaude] = useState(null)
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState(null)
  const [editando, setEditando] = useState(null)

  const carregar = useCallback(async () => {
    setCarregando(true)
    setErro(null)
    try {
      const [resumoNovo, mesesNovos, notasNovas] = await Promise.all([
        api.resumo(mes),
        api.meses(),
        api.notas(),
      ])
      setResumo(resumoNovo)
      setMeses(mesesNovos)
      setNotas(notasNovas)
    } catch (e) {
      setErro(e.message)
    } finally {
      setCarregando(false)
    }
  }, [mes])

  useEffect(() => {
    carregar()
  }, [carregar])

  useEffect(() => {
    api.health().then(setSaude).catch(() => setSaude(null))
  }, [])

  // O mês atual pode ainda não ter nota; ele entra na lista mesmo assim para
  // não sumir do seletor logo depois de trocar de mês.
  const opcoesMes = [...new Set([mes, ...meses.map((m) => m.periodo)])].sort().reverse()

  const topItens =
    resumo?.itens.slice(0, TOP_N).map((i) => ({
      chave: i.chave,
      nome: i.nome,
      valor: i.valor_total,
      detalhe: `${i.ocorrencias}x`,
    })) ?? []

  const categorias =
    resumo?.categorias.map((c) => ({
      chave: c.categoria,
      nome: rotuloCategoria(c.categoria),
      valor: c.valor_total,
      detalhe: `${c.itens} ${c.itens === 1 ? 'item' : 'itens'}`,
    })) ?? []

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">🧾</span>
          <h1>SmartNotas</h1>
          <span className="brand-sub">gastos do supermercado, somados por produto</span>
        </div>

        <label htmlFor="mes" className="sr-only">
          Período
        </label>
        <select
          id="mes"
          className="select"
          value={mes}
          onChange={(e) => setMes(e.target.value)}
        >
          {opcoesMes.map((periodo) => {
            const info = meses.find((m) => m.periodo === periodo)
            return (
              <option key={periodo} value={periodo}>
                {periodoLongo(periodo)}
                {info ? ` — ${moeda(info.total_gasto)}` : ''}
              </option>
            )
          })}
        </select>

        <button className="btn btn-ghost" onClick={carregar} disabled={carregando}>
          {carregando ? <span className="spinner" /> : null}
          Atualizar
        </button>
      </header>

      {saude && !saude.ia_configurada ? (
        <div className="banner banner-warning">
          <span>🔑</span>
          <span>
            A leitura por IA ainda não está ativa. Copie <code>backend/.env.example</code> para{' '}
            <code>backend/.env</code> e preencha <code>GEMINI_API_KEY</code> com uma chave
            gerada em aistudio.google.com/apikey — depois reinicie o backend. O resto do
            dashboard já funciona.
          </span>
        </div>
      ) : null}

      {erro ? (
        <div className="banner banner-critical">
          <span>⚠</span>
          <span>
            Não consegui falar com o backend: {erro}. Confira se ele está rodando em
            127.0.0.1:8000.
          </span>
        </div>
      ) : null}

      <Upload onConcluido={carregar} iaConfigurada={Boolean(saude?.ia_configurada)} />

      {resumo ? (
        <>
          <Tiles resumo={resumo} />

          <div className="grid-2">
            <section className="card">
              <div className="card-head">
                <h2>Onde o dinheiro foi</h2>
              </div>
              <p className="card-sub">
                Os {TOP_N} produtos que mais pesaram em {periodoLongo(resumo.periodo)}.
              </p>
              <BarList dados={topItens} />
            </section>

            <section className="card">
              <div className="card-head">
                <h2>Por categoria</h2>
              </div>
              <p className="card-sub">Total gasto em cada tipo de produto.</p>
              <BarList dados={categorias} />
            </section>
          </div>

          <section className="card">
            <div className="card-head">
              <h2>Itens somados no mês</h2>
            </div>
            <p className="card-sub">
              Cada linha junta o mesmo produto comprado em datas diferentes. Clique num
              cabeçalho para reordenar.
            </p>
            <TabelaItens itens={resumo.itens} onEditar={setEditando} />
          </section>
        </>
      ) : null}

      <section className="card">
        <div className="card-head">
          <h2>Notas enviadas</h2>
        </div>
        <p className="card-sub">Todas as notas do banco, de todos os períodos.</p>
        <ListaNotas notas={notas} onMudou={carregar} />
      </section>

      {editando ? (
        <EditarItem
          item={editando}
          onFechar={() => setEditando(null)}
          onSalvo={carregar}
        />
      ) : null}
    </div>
  )
}
