import { useEffect, useState } from 'react'
import type { Product } from '../types'
import { currency, number } from '../lib/format'
import { ErrorBanner, Modal } from './ui'

export default function RestockModal({
  product,
  onClose,
  onSubmit,
  submitting = false,
  error,
}: {
  product: Product | null
  onClose: () => void
  onSubmit: (quantity: number, note: string) => Promise<void>
  submitting?: boolean
  error?: string | null
}) {
  const [quantity, setQuantity] = useState(1)
  const [note, setNote] = useState('')

  useEffect(() => {
    if (!product) return
    setQuantity(Math.max(product.reorder_level - product.stock_quantity, 1))
    setNote('')
  }, [product])

  if (!product) return null

  const projected = product.stock_quantity + quantity

  return (
    <Modal
      open={Boolean(product)}
      title={`Restock ${product.name}`}
      onClose={onClose}
      footer={
        <div className="flex items-center justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={submitting}>
            Cancel
          </button>
          <button
            type="button"
            className="btn-primary"
            disabled={submitting || quantity <= 0}
            onClick={() => onSubmit(quantity, note)}
          >
            {submitting ? 'Updating…' : 'Add stock'}
          </button>
        </div>
      }
    >
      <div className="space-y-4">
        <ErrorBanner message={error} />
        <div className="grid grid-cols-3 gap-3 rounded-lg bg-slate-50 p-3 text-center text-sm">
          <div>
            <p className="text-xs uppercase text-slate-500">Current</p>
            <p className="font-semibold">{number(product.stock_quantity)}</p>
          </div>
          <div>
            <p className="text-xs uppercase text-slate-500">Reorder at</p>
            <p className="font-semibold">{number(product.reorder_level)}</p>
          </div>
          <div>
            <p className="text-xs uppercase text-slate-500">After</p>
            <p className="font-semibold">{number(projected)}</p>
          </div>
        </div>

        <div>
          <label className="label" htmlFor="restock-quantity">
            Quantity to add
          </label>
          <input
            id="restock-quantity"
            className="input"
            type="number"
            min={1}
            value={quantity}
            onChange={(event) => setQuantity(Number(event.target.value))}
          />
          <p className="mt-1 text-xs text-slate-500">
            Stock value added: {currency(quantity * product.unit_price)}
          </p>
        </div>

        <div>
          <label className="label" htmlFor="restock-note">
            Note (optional)
          </label>
          <input
            id="restock-note"
            className="input"
            placeholder="Purchase order, delivery reference…"
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
        </div>
      </div>
    </Modal>
  )
}
