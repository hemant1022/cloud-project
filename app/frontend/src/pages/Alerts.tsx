import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, RefreshCw, XCircle } from 'lucide-react'
import { useState } from 'react'
import { adjustStock, apiErrorMessage, fetchLowStock } from '../api'
import { useAuth } from '../auth/AuthContext'
import RestockModal from '../components/RestockModal'
import { Badge, EmptyState, ErrorBanner, PageHeader, Spinner, SuccessBanner } from '../components/ui'
import { currency, number } from '../lib/format'
import type { Product } from '../types'

type Tab = 'low' | 'out'

export default function Alerts() {
  const { user } = useAuth()
  const canWrite = user?.role === 'admin' || user?.role === 'manager'
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<Tab>('low')
  const [restocking, setRestocking] = useState<Product | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [restockError, setRestockError] = useState<string | null>(null)

  const alertsQuery = useQuery({ queryKey: ['low-stock'], queryFn: fetchLowStock })

  const restockMutation = useMutation({
    mutationFn: ({ id, changeQty, note }: { id: number; changeQty: number; note: string }) =>
      adjustStock(id, changeQty, 'RESTOCK', note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['low-stock'] })
      queryClient.invalidateQueries({ queryKey: ['products'] })
      queryClient.invalidateQueries({ queryKey: ['summary'] })
    },
  })

  const handleRestock = async (quantity: number, note: string) => {
    if (!restocking) return
    setRestockError(null)
    try {
      await restockMutation.mutateAsync({ id: restocking.id, changeQty: quantity, note })
      setMessage(`${restocking.name} restocked by ${quantity}`)
      setRestocking(null)
    } catch (err) {
      setRestockError(apiErrorMessage(err))
    }
  }

  const items = alertsQuery.data ?? []
  const lowItems = items.filter((product) => !product.is_out_of_stock)
  const outItems = items.filter((product) => product.is_out_of_stock)
  const visible = tab === 'low' ? lowItems : outItems

  return (
    <div>
      <PageHeader
        title="Stock alerts"
        subtitle="Products at or below their reorder level, with one-click restocking."
      />

      <div className="mb-4 space-y-3">
        <SuccessBanner message={message} />
        <ErrorBanner message={error} />
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setTab('low')}
          className={tab === 'low' ? 'btn-primary' : 'btn-secondary'}
        >
          <AlertTriangle className="h-4 w-4" />
          Low stock ({lowItems.length})
        </button>
        <button
          type="button"
          onClick={() => setTab('out')}
          className={tab === 'out' ? 'btn-primary' : 'btn-secondary'}
        >
          <XCircle className="h-4 w-4" />
          Out of stock ({outItems.length})
        </button>
      </div>

      <div className="card overflow-hidden">
        {alertsQuery.isLoading ? (
          <Spinner label="Loading alerts…" />
        ) : alertsQuery.error ? (
          <div className="p-4">
            <ErrorBanner message={apiErrorMessage(alertsQuery.error)} />
          </div>
        ) : visible.length === 0 ? (
          <EmptyState
            title={tab === 'low' ? 'No low-stock products' : 'No out-of-stock products'}
            description={
              tab === 'low'
                ? 'Everything is above its reorder level.'
                : 'Nothing is completely out of stock.'
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="table-head">
                <tr>
                  <th className="px-4 py-3">Product</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Supplier</th>
                  <th className="px-4 py-3 text-right">Stock</th>
                  <th className="px-4 py-3 text-right">Reorder at</th>
                  <th className="px-4 py-3 text-right">Deficit</th>
                  <th className="px-4 py-3 text-right">Restock value</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {visible.map((product) => (
                  <tr key={product.id} className="hover:bg-slate-50/60">
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-900">{product.name}</p>
                      <p className="text-xs text-slate-500">{product.sku}</p>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{product.category_name ?? '—'}</td>
                    <td className="px-4 py-3 text-slate-600">{product.supplier_name ?? '—'}</td>
                    <td className="px-4 py-3 text-right font-medium">{number(product.stock_quantity)}</td>
                    <td className="px-4 py-3 text-right text-slate-600">{number(product.reorder_level)}</td>
                    <td className="px-4 py-3 text-right font-medium text-rose-600">{number(product.deficit)}</td>
                    <td className="px-4 py-3 text-right">{currency(product.deficit * product.unit_price)}</td>
                    <td className="px-4 py-3">
                      {product.is_out_of_stock ? (
                        <Badge tone="red">Out of stock</Badge>
                      ) : (
                        <Badge tone="amber">Low stock</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {canWrite && (
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={() => {
                            setRestockError(null)
                            setRestocking(product)
                          }}
                        >
                          <RefreshCw className="h-4 w-4" />
                          Restock
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <RestockModal
        product={restocking}
        onClose={() => setRestocking(null)}
        onSubmit={handleRestock}
        submitting={restockMutation.isPending}
        error={restockError}
      />
    </div>
  )
}
