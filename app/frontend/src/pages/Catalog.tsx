import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import {
  apiErrorMessage,
  createCategory,
  createSupplier,
  deleteCategory,
  deleteSupplier,
  fetchCategories,
  fetchSuppliers,
} from '../api'
import { useAuth } from '../auth/AuthContext'
import { EmptyState, ErrorBanner, PageHeader, Spinner, SuccessBanner } from '../components/ui'

export default function Catalog() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const queryClient = useQueryClient()

  const [categoryName, setCategoryName] = useState('')
  const [supplierName, setSupplierName] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: fetchCategories })
  const suppliersQuery = useQuery({ queryKey: ['suppliers'], queryFn: fetchSuppliers })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['categories'] })
    queryClient.invalidateQueries({ queryKey: ['suppliers'] })
  }

  const addCategoryMutation = useMutation({
    mutationFn: (name: string) => createCategory(name),
    onSuccess: invalidate,
  })
  const addSupplierMutation = useMutation({
    mutationFn: (name: string) => createSupplier(name),
    onSuccess: invalidate,
  })
  const deleteCategoryMutation = useMutation({ mutationFn: deleteCategory, onSuccess: invalidate })
  const deleteSupplierMutation = useMutation({ mutationFn: deleteSupplier, onSuccess: invalidate })

  const addCategory = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!categoryName.trim()) return
    setMessage(null)
    setError(null)
    try {
      await addCategoryMutation.mutateAsync(categoryName.trim())
      setMessage(`Category "${categoryName.trim()}" added`)
      setCategoryName('')
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

  const addSupplier = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!supplierName.trim()) return
    setMessage(null)
    setError(null)
    try {
      await addSupplierMutation.mutateAsync(supplierName.trim())
      setMessage(`Supplier "${supplierName.trim()}" added`)
      setSupplierName('')
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

  const removeCategory = async (id: number, name: string) => {
    if (!window.confirm(`Delete category "${name}"? Products will keep their data but lose this category.`)) return
    setMessage(null)
    setError(null)
    try {
      await deleteCategoryMutation.mutateAsync(id)
      setMessage(`Category "${name}" deleted`)
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

  const removeSupplier = async (id: number, name: string) => {
    if (!window.confirm(`Delete supplier "${name}"? Products will keep their data but lose this supplier.`)) return
    setMessage(null)
    setError(null)
    try {
      await deleteSupplierMutation.mutateAsync(id)
      setMessage(`Supplier "${name}" deleted`)
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

  return (
    <div>
      <PageHeader
        title="Catalog"
        subtitle="Categories and suppliers used to classify and source your products."
      />

      <div className="mb-4 space-y-3">
        <SuccessBanner message={message} />
        <ErrorBanner message={error} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Categories</h2>
            <span className="text-xs text-slate-500">{categoriesQuery.data?.length ?? 0} total</span>
          </div>

          {isAdmin && (
            <form onSubmit={addCategory} className="mt-4 flex gap-2">
              <input
                className="input"
                placeholder="New category name"
                value={categoryName}
                onChange={(event) => setCategoryName(event.target.value)}
              />
              <button type="submit" className="btn-primary shrink-0" disabled={addCategoryMutation.isPending}>
                <Plus className="h-4 w-4" />
                Add
              </button>
            </form>
          )}

          <div className="mt-4">
            {categoriesQuery.isLoading ? (
              <Spinner label="Loading categories…" />
            ) : (categoriesQuery.data ?? []).length === 0 ? (
              <EmptyState title="No categories yet" />
            ) : (
              <ul className="divide-y divide-slate-100">
                {(categoriesQuery.data ?? []).map((category) => (
                  <li key={category.id} className="flex items-center justify-between gap-3 py-2.5">
                    <div>
                      <p className="text-sm font-medium text-slate-800">{category.name}</p>
                      {category.description && (
                        <p className="text-xs text-slate-500">{category.description}</p>
                      )}
                    </div>
                    {isAdmin && (
                      <button
                        type="button"
                        className="rounded-md p-1.5 text-rose-500 hover:bg-rose-50"
                        onClick={() => removeCategory(category.id, category.name)}
                        title="Delete category"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Suppliers</h2>
            <span className="text-xs text-slate-500">{suppliersQuery.data?.length ?? 0} total</span>
          </div>

          {isAdmin && (
            <form onSubmit={addSupplier} className="mt-4 flex gap-2">
              <input
                className="input"
                placeholder="New supplier name"
                value={supplierName}
                onChange={(event) => setSupplierName(event.target.value)}
              />
              <button type="submit" className="btn-primary shrink-0" disabled={addSupplierMutation.isPending}>
                <Plus className="h-4 w-4" />
                Add
              </button>
            </form>
          )}

          <div className="mt-4">
            {suppliersQuery.isLoading ? (
              <Spinner label="Loading suppliers…" />
            ) : (suppliersQuery.data ?? []).length === 0 ? (
              <EmptyState title="No suppliers yet" />
            ) : (
              <ul className="divide-y divide-slate-100">
                {(suppliersQuery.data ?? []).map((supplier) => (
                  <li key={supplier.id} className="flex items-center justify-between gap-3 py-2.5">
                    <div>
                      <p className="text-sm font-medium text-slate-800">{supplier.name}</p>
                      <p className="text-xs text-slate-500">
                        {[supplier.country, supplier.email].filter(Boolean).join(' · ') || 'No contact details'}
                      </p>
                    </div>
                    {isAdmin && (
                      <button
                        type="button"
                        className="rounded-md p-1.5 text-rose-500 hover:bg-rose-50"
                        onClick={() => removeSupplier(supplier.id, supplier.name)}
                        title="Delete supplier"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
