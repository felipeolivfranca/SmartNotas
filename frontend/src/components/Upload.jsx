import { useRef, useState } from 'react'
import { api } from '../api'
import { moeda } from '../formato'

const ACEITOS = 'image/jpeg,image/png,image/webp,application/pdf'

export default function Upload({ onConcluido, iaConfigurada }) {
  const [enviando, setEnviando] = useState(false)
  const [arrastando, setArrastando] = useState(false)
  const [resultados, setResultados] = useState([])
  const [erro, setErro] = useState(null)
  const inputRef = useRef(null)

  async function enviar(arquivos) {
    const lista = Array.from(arquivos ?? [])
    if (!lista.length) return

    setEnviando(true)
    setErro(null)
    setResultados([])

    try {
      const retorno = await api.upload(lista)
      setResultados(retorno)
      // Recarrega o dashboard se ao menos uma nota entrou.
      if (retorno.some((r) => r.sucesso)) onConcluido?.()
    } catch (e) {
      setErro(e.message)
    } finally {
      setEnviando(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <div className="card">
      <div className="card-head">
        <h2>Enviar nota fiscal</h2>
      </div>
      <p className="card-sub">
        A foto é lida pela IA e vira linhas de produto somadas no dashboard.
      </p>

      <button
        type="button"
        className={`drop${arrastando ? ' dragging' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setArrastando(true)
        }}
        onDragLeave={() => setArrastando(false)}
        onDrop={(e) => {
          e.preventDefault()
          setArrastando(false)
          enviar(e.dataTransfer.files)
        }}
        disabled={enviando}
      >
        {enviando ? (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 9 }}>
            <span className="spinner" />
            Lendo a nota com a IA — pode levar alguns segundos…
          </span>
        ) : (
          <>
            <div className="drop-title">Arraste as fotos aqui ou clique para escolher</div>
            <div className="drop-hint">JPG, PNG, WEBP ou PDF · até 20 MB por arquivo</div>
          </>
        )}
      </button>

      <input
        ref={inputRef}
        type="file"
        accept={ACEITOS}
        multiple
        hidden
        onChange={(e) => enviar(e.target.files)}
      />

      {!iaConfigurada ? (
        <p className="field-hint" style={{ marginTop: 10 }}>
          A chave da IA ainda não foi configurada — o envio vai falhar até você criar o
          arquivo <code>backend/.env</code>.
        </p>
      ) : null}

      {erro ? (
        <div className="banner banner-critical" style={{ marginTop: 14, marginBottom: 0 }}>
          <span>⚠</span>
          <span>{erro}</span>
        </div>
      ) : null}

      {resultados.length ? (
        <ul className="results">
          {resultados.map((r, i) => (
            <li key={`${r.arquivo}-${i}`} className={`result ${r.sucesso ? 'result-ok' : 'result-fail'}`}>
              <span className="result-icon">{r.sucesso ? '✓' : '✕'}</span>
              <span>
                <span className="result-file">{r.arquivo}</span>
                {r.sucesso ? (
                  <span className="result-msg">
                    {' '}
                    — {r.qtd_itens} {r.qtd_itens === 1 ? 'item lido' : 'itens lidos'}
                    {r.total != null ? `, ${moeda(r.total)}` : ''}
                  </span>
                ) : null}
                {r.mensagem ? <div className="result-msg">{r.mensagem}</div> : null}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
