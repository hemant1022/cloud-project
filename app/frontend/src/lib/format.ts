const usd = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 2,
})

const integer = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })

export function currency(value: number | null | undefined): string {
  return usd.format(Number(value ?? 0))
}

export function number(value: number | null | undefined): string {
  return integer.format(Number(value ?? 0))
}

export function dateTime(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function percent(value: number): string {
  return `${Math.round(value)}%`
}
