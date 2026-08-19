// Formatação pt-BR usada em toda a interface.

const MOEDA = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

const MOEDA_CURTA = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  maximumFractionDigits: 0,
})

export function moeda(valor) {
  return MOEDA.format(valor ?? 0)
}

export function moedaCurta(valor) {
  return MOEDA_CURTA.format(valor ?? 0)
}

// Quantidade vem fracionária para produtos a peso (0,436 KG) e inteira para
// unidades — mostrar "3,000 requeijões" seria ruído.
export function quantidade(valor) {
  const numero = valor ?? 0
  const casas = Number.isInteger(numero) ? 0 : 3
  return numero.toLocaleString('pt-BR', {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  })
}

export function dataCurta(iso) {
  if (!iso) return '—'
  const [ano, mes, dia] = iso.slice(0, 10).split('-')
  return `${dia}/${mes}/${ano}`
}

const MESES = [
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
]

export function periodoLongo(periodo) {
  if (!periodo) return ''
  const [ano, mes] = periodo.split('-')
  return `${MESES[Number(mes) - 1]} de ${ano}`
}

export function periodoAtual() {
  const hoje = new Date()
  return `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, '0')}`
}

export const CATEGORIAS = {
  laticinios: 'Laticínios',
  carnes: 'Carnes',
  frutas_verduras: 'Frutas e verduras',
  padaria: 'Padaria',
  mercearia: 'Mercearia',
  bebidas: 'Bebidas',
  congelados: 'Congelados',
  limpeza: 'Limpeza',
  higiene: 'Higiene',
  pet: 'Pet',
  outros: 'Outros',
}

export function rotuloCategoria(chave) {
  return CATEGORIAS[chave] ?? chave
}
