import { useState } from 'react'
import { api } from '../api'

const SENHA_MIN = 8

/**
 * Porta de entrada do app: entrar ou criar conta, na mesma tela.
 *
 * Só existem dois modos e eles compartilham e-mail e senha, então separar em
 * duas rotas custaria mais do que alternar um estado — e quem errou de modo
 * troca sem redigitar o que já preencheu.
 */
export default function Login({ onEntrou }) {
  const [modo, setModo] = useState('entrar')
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState(null)

  const criando = modo === 'criar'

  function trocarModo(novo) {
    setModo(novo)
    setErro(null)
  }

  async function enviar(evento) {
    evento.preventDefault()
    setEnviando(true)
    setErro(null)
    try {
      const usuario = criando
        ? await api.registrar(nome, email, senha)
        : await api.login(email, senha)
      // O backend já devolve a conta logada com o cookie de sessão setado.
      onEntrou(usuario)
    } catch (e) {
      setErro(e.message)
      setEnviando(false)
    }
  }

  return (
    <div className="auth-tela">
      <div className="auth-card">
        <div className="auth-brand">
          <span className="brand-mark">🧾</span>
          <h1>SmartNotas</h1>
        </div>
        <p className="card-sub auth-sub">
          Seus gastos do supermercado, somados por produto. Cada conta vê apenas as
          próprias notas.
        </p>

        <div className="auth-abas" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={!criando}
            className={`auth-aba${!criando ? ' ativa' : ''}`}
            onClick={() => trocarModo('entrar')}
          >
            Entrar
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={criando}
            className={`auth-aba${criando ? ' ativa' : ''}`}
            onClick={() => trocarModo('criar')}
          >
            Criar conta
          </button>
        </div>

        <form onSubmit={enviar}>
          {criando ? (
            <div className="field">
              <label htmlFor="nome">Nome</label>
              <input
                id="nome"
                className="input"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                autoComplete="name"
                required
                autoFocus
              />
            </div>
          ) : null}

          <div className="field">
            <label htmlFor="email">E-mail</label>
            <input
              id="email"
              type="email"
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
              autoFocus={!criando}
            />
          </div>

          <div className="field">
            <label htmlFor="senha">Senha</label>
            <input
              id="senha"
              type="password"
              className="input"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              // O navegador precisa saber se está criando ou conferindo senha
              // para oferecer a do cofre em vez de sugerir uma nova.
              autoComplete={criando ? 'new-password' : 'current-password'}
              minLength={criando ? SENHA_MIN : undefined}
              required
            />
            {criando ? (
              <div className="field-hint">Pelo menos {SENHA_MIN} caracteres.</div>
            ) : null}
          </div>

          {erro ? (
            <div className="banner banner-critical" style={{ marginBottom: 14 }}>
              <span>⚠</span>
              <span>{erro}</span>
            </div>
          ) : null}

          <button type="submit" className="btn auth-enviar" disabled={enviando}>
            {enviando ? <span className="spinner" /> : null}
            {criando ? 'Criar conta e entrar' : 'Entrar'}
          </button>
        </form>

        <p className="auth-rodape">
          O app roda na sua máquina: a senha é guardada como hash bcrypt e as notas
          ficam no SQLite local.
        </p>
      </div>
    </div>
  )
}
