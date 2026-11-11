import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ChevronLeft,
  ChevronRight,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  XCircle,
} from 'lucide-react'
import { useState } from 'react'
import {
  adjustStock,
  apiErrorMessage,
  createProduct,
  deleteProduct,
  fetchCategories,
  fetchProducts,
  fetchSuppliers,
  updateProduct,
} from '../api'
import { useAuth } from '../auth/AuthContext'
import ProductForm from '../components/ProductForm'
import RestockModal from '../components/RestockModal'
import { Badge, EmptyState, ErrorBanner, PageHeader, Spinner, SuccessBanner } from '../components/ui'
import { currency, number } from '../lib/format'
import type { Product, ProductFilters, ProductInput } from '../types'

const DEFAULT_FILTERS: ProductFilters = {
  page: 1,
  page_size: 10,
  stock_status: 'all',
  sort: 'name',
  order: 'asc',
}

function stockBadge(product: Product) {
  if (product.is_out_of_stock) return <Badge tone="red">Out of stock</Badge>
  if (product.is_low_stock) return <Badge tone="amber">Low stock</Badge>
  return <Badge tone="green">In stock</Badge>
}

export default function Products() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const canWrite = user?.role === 'admin' || user?.role === 'manager'
  const canDelete = user?.role === 'admin'

  const [filters, setFilters] = useState<ProductFilters>(DEFAULT_FILTERS)
  const [searchInput, setSearchInput] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Product | null>(null)
  const [restocking, setRestocking] = useState<Product | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [restockError, setRestockError] = useState<string | null>(null)

  const productsQuery = useQuery({
    queryKey: ['products', filters],
    queryFn: () => fetchProducts(filters),
    placeholderData: keepPreviousData,
  })
  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: fetchCategories })
  const suppliersQuery = useQuery({ queryKey: ['suppliers'], queryFn: fetchSuppliers })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['products'] })
    queryClient.invalidateQueries({ queryKey: ['summary'] })
    queryClient.invalidateQueries({ queryKey: ['low-stock'] })
  }

  const createMutation = useMutation({ mutationFn: createProduct, onSuccess: invalidate })
  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ProductInput }) => updateProduct(id, payload),
    onSuccess: invalidate,
  })
  const deleteMutation = useMutation({ mutationFn: deleteProduct, onSuccess: invalidate })
  const restockMutation = useMutation({
    mutationFn: ({ id, changeQty, note }: { id: number; changeQty: number; note: string }) =>
      adjustStock(id, changeQty, 'RESTOCK', note),
    onSuccess: invalidate,
  })

  const handleSubmit = async (payload: ProductInput) => {
    setMessage(null)
    setError(null)
    if (editing) {
      await updateMutation.mutateAsync({ id: editing.id, payload })
      setMessage(`${payload.name} updated`)
      setEditing(null)
    } else {
      await createMutation.mutateAsync(payload)
      setMessage(`${payload.name} created`)
    }
  }

  const handleDelete = async (product: Product) => {
    if (!window.confirm(`Delete ${product.name} (${product.sku})? This cannot be undone.`)) return
    setMessage(null)
    setError(null)
    try {
      await deleteMutation.mutateAsync(product.id)
      setMessage(`${product.name} deleted`)
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

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

  const updateFilter = (patch: Partial<ProductFilters>) => {
    setFilters((current) => ({ ...current, ...patch, page: 1 }))
  }

  const toggleSort = (column: string) => {
    setFilters((current) => ({
      ...current,
      sort: column,
      order: current.sort === column && current.order === 'asc' ? 'desc' : 'asc',
      page: 1,
    }))
  }

  const applySearch = (event: React.FormEvent) => {
    event.preventDefault()
    updateFilter({ q: searchInput.trim() || undefined })
  }

  const resetFilters = () => {
    setSearchInput('')
    setFilters(DEFAULT_FILTERS)
  }

  const data = productsQuery.data
  const sortIndicator = (column: string) =>
    filters.sort === column ? (filters.order === 'asc' ? ' ↑' : ' ↓') : ''

  return (
    <div>
      <PageHeader
        title="Products"
        subtitle="Search, filter, and maintain every SKU in your inventory."
        actions={
          canWrite ? (
            <button
              type="button"
              className="btn-primary"
              onClick={() => {
                setEditing(null)
                setFormOpen(true)
              }}
            >
              <Plus className="h-4 w-4" />
              Add product
            </button>
          ) : null
        }
      />

      <div className="mb-4 space-y-3">
        <SuccessBanner message={message} />
        <ErrorBanner message={error} />
      </div>

      <div className="card mb-4 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
          <form onSubmit={applySearch} className="flex flex-1 gap-2">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                className="input pl-9"
                placeholder="Search by name, SKU, or description…"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
              />
            </div>
            <button type="submit" className="btn-secondary">
              Search
            </button>
          </form>

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:w-auto">
            <select
              className="input"
              value={filters.category_id ?? ''}
              onChange={(event) =>
                updateFilter({ category_id: event.target.value ? Number(event.target.value) : undefined })
              }
            >
              <option value="">All categories</option>
              {(categoriesQuery.data ?? []).map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
            <select
              className="input"
              value={filters.supplier_id ?? ''}
              onChange={(event) =>
                updateFilter({ supplier_id: event.target.value ? Number(event.target.value) : undefined })
              }
            >
              <option value="">All suppliers</option>
              {(suppliersQuery.data ?? []).map((supplier) => (
                <option key={supplier.id} value={supplier.id}>
                  {supplier.name}
                </option>
              ))}
            </select>
            <select
              className="input"
              value={filters.stock_status ?? 'all'}
              onChange={(event) =>
                updateFilter({ stock_status: event.target.value as ProductFilters['stock_status'] })
              }
            >
              <option value="all">All stock</option>
              <option value="in">In stock</option>
              <option value="low">Low stock</option>
              <option value="out">Out of stock</option>
            </select>
          </div>

          <button type="button" className="btn-secondary" onClick={resetFilters}>
            <RefreshCw className="h-4 w-4" />
            Reset
          </button>
        </div>
      </div>

      <div className="card overflow-hidden">
        {productsQuery.isLoading ? (
          <Spinner label="Loading products…" />
        ) : productsQuery.error ? (
          <div className="p-4">
            <ErrorBanner message={apiErrorMessage(productsQuery.error)} />
          </div>
        ) : !data || data.items.length === 0 ? (
          <EmptyState
            title="No products found"
            description="Adjust your filters or add a product to get started."
            action={
              canWrite ? (
                <button type="button" className="btn-primary" onClick={() => setFormOpen(true)}>
                  <Plus className="h-4 w-4" />
                  Add product
                </button>
              ) : undefined
            }
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="table-head">
                  <tr>
                    <th className="cursor-pointer px-4 py-3" onClick={() => toggleSort('name')}>
                      Product{sortIndicator('name')}
                    </th>
                    <th className="px-4 py-3">Category</th>
                    <th className="px-4 py-3">Supplier</th>
                    <th className="cursor-pointer px-4 py-3 text-right" onClick={() => toggleSort('unit_price')}>
                      Price{sortIndicator('unit_price')}
                    </th>
                    <th className="cursor-pointer px-4 py-3 text-right" onClick={() => toggleSort('stock_quantity')}>
                      Stock{sortIndicator('stock_quantity')}
                    </th>
                    <th className="px-4 py-3">Status</th>
                    <th className="cursor-pointer px-4 py-3 text-right" onClick={() => toggleSort('inventory_value')}>
                      Value{sortIndicator('inventory_value')}
                    </th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.items.map((product) => (
                    <tr key={product.id} className="hover:bg-slate-50/60">
                      <td className="px-4 py-3">
                        <p className="font-medium text-slate-900">{product.name}</p>
                        <p className="text-xs text-slate-500">{product.sku}</p>
                      </td>
                      <td className="px-4 py-3 text-slate-600">{product.category_name ?? '—'}</td>
                      <td className="px-4 py-3 text-slate-600">{product.supplier_name ?? '—'}</td>
                      <td className="px-4 py-3 text-right">{currency(product.unit_price)}</td>
                      <td className="px-4 py-3 text-right">
                        <span className="font-medium">{number(product.stock_quantity)}</span>
                        <span className="block text-xs text-slate-500">reorder at {number(product.reorder_level)}</span>
                      </td>
                      <td className="px-4 py-3">{stockBadge(product)}</td>
                      <td className="px-4 py-3 text-right font-medium">{currency(product.inventory_value)}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          {canWrite && (
                            <>
                              <button
                                type="button"
                                className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                                title="Restock"
                                onClick={() => {
                                  setRestockError(null)
                                  setRestocking(product)
                                }}
                              >
                                <RefreshCw className="h-4 w-4" />
                              </button>
                              <button
                                type="button"
                                className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                                title="Edit"
                                onClick={() => {
                                  setEditing(product)
                                  setFormOpen(true)
                                }}
                              >
                                <Pencil className="h-4 w-4" />
                              </button>
                            </>
                          )}
                          {canDelete && (
                            <button
                              type="button"
                              className="rounded-md p-1.5 text-rose-500 hover:bg-rose-50 hover:text-rose-700"
                              title="Delete"
                              onClick={() => handleDelete(product)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex flex-col items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 text-sm text-slate-600 sm:flex-row">
              <p>
                Showing {(data.page - 1) * data.page_size + 1}–
                {Math.min(data.page * data.page_size, data.total)} of {number(data.total)}
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={data.page <= 1}
                  onClick={() => setFilters((current) => ({ ...current, page: (current.page ?? 1) - 1 }))}
                >
                  <ChevronLeft className="h-4 w-4" /> Prev
                </button>
                <span>
                  Page {data.page} of {data.pages || 1}
                </span>
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={data.page >= data.pages}
                  onClick={() => setFilters((current) => ({ ...current, page: (current.page ?? 1) + 1 }))}
                >
                  Next <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {!productsQuery.isLoading && !productsQuery.error && data && data.total === 0 && filters.q && (
        <p className="mt-3 flex items-center gap-1 text-xs text-slate-500">
          <XCircle className="h-3 w-3" /> No matches for “{filters.q}”.
        </p>
      )}

      <ProductForm
        open={formOpen}
        product={editing}
        categories={categoriesQuery.data ?? []}
        suppliers={suppliersQuery.data ?? []}
        onClose={() => {
          setFormOpen(false)
          setEditing(null)
        }}
        onSubmit={handleSubmit}
        submitting={createMutation.isPending || updateMutation.isPending}
      />

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
