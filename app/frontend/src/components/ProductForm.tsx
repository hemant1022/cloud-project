import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { apiErrorMessage } from '../api'
import type { Category, Product, ProductInput, Supplier } from '../types'
import { ErrorBanner, Modal } from './ui'

const schema = z.object({
  sku: z.string().trim().min(1, 'SKU is required').max(64),
  name: z.string().trim().min(1, 'Name is required').max(200),
  description: z.string().optional(),
  category_id: z.string().optional(),
  supplier_id: z.string().optional(),
  unit_price: z.number({ invalid_type_error: 'Enter a price' }).min(0, 'Must be zero or greater'),
  cost_price: z.number({ invalid_type_error: 'Enter a cost' }).min(0, 'Must be zero or greater'),
  stock_quantity: z.number({ invalid_type_error: 'Enter a quantity' }).int().min(0),
  reorder_level: z.number({ invalid_type_error: 'Enter a reorder level' }).int().min(0),
})

type FormValues = z.infer<typeof schema>

const emptyValues: FormValues = {
  sku: '',
  name: '',
  description: '',
  category_id: '',
  supplier_id: '',
  unit_price: 0,
  cost_price: 0,
  stock_quantity: 0,
  reorder_level: 10,
}

export default function ProductForm({
  open,
  product,
  categories,
  suppliers,
  onClose,
  onSubmit,
  submitting = false,
}: {
  open: boolean
  product?: Product | null
  categories: Category[]
  suppliers: Supplier[]
  onClose: () => void
  onSubmit: (payload: ProductInput) => Promise<void>
  submitting?: boolean
}) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: emptyValues })
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setFormError(null)
    reset(
      product
        ? {
            sku: product.sku,
            name: product.name,
            description: product.description ?? '',
            category_id: product.category_id ? String(product.category_id) : '',
            supplier_id: product.supplier_id ? String(product.supplier_id) : '',
            unit_price: product.unit_price,
            cost_price: product.cost_price,
            stock_quantity: product.stock_quantity,
            reorder_level: product.reorder_level,
          }
        : emptyValues,
    )
  }, [open, product, reset])

  const submit = handleSubmit(async (values) => {
    setFormError(null)
    const payload: ProductInput = {
      sku: values.sku.trim(),
      name: values.name.trim(),
      description: values.description?.trim() || null,
      category_id: values.category_id ? Number(values.category_id) : null,
      supplier_id: values.supplier_id ? Number(values.supplier_id) : null,
      unit_price: values.unit_price,
      cost_price: values.cost_price,
      stock_quantity: values.stock_quantity,
      reorder_level: values.reorder_level,
    }
    try {
      await onSubmit(payload)
      onClose()
    } catch (error) {
      setFormError(apiErrorMessage(error))
    }
  })

  return (
    <Modal
      open={open}
      title={product ? `Edit ${product.name}` : 'Add product'}
      onClose={onClose}
      wide
      footer={
        <div className="flex items-center justify-end gap-2">
          <button type="button" onClick={onClose} className="btn-secondary" disabled={submitting}>
            Cancel
          </button>
          <button type="submit" form="product-form" className="btn-primary" disabled={submitting}>
            {submitting ? 'Saving…' : product ? 'Save changes' : 'Create product'}
          </button>
        </div>
      }
    >
      <form id="product-form" onSubmit={submit} className="space-y-4">
        <ErrorBanner message={formError} />

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="sku">
              SKU
            </label>
            <input id="sku" className="input" placeholder="SKU-1001" {...register('sku')} />
            {errors.sku && <p className="mt-1 text-xs text-rose-600">{errors.sku.message}</p>}
          </div>
          <div>
            <label className="label" htmlFor="name">
              Name
            </label>
            <input id="name" className="input" placeholder="Wireless Mouse" {...register('name')} />
            {errors.name && <p className="mt-1 text-xs text-rose-600">{errors.name.message}</p>}
          </div>
        </div>

        <div>
          <label className="label" htmlFor="description">
            Description
          </label>
          <textarea id="description" rows={2} className="input" placeholder="Optional details" {...register('description')} />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="category_id">
              Category
            </label>
            <select id="category_id" className="input" {...register('category_id')}>
              <option value="">— Select category —</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="supplier_id">
              Supplier
            </label>
            <select id="supplier_id" className="input" {...register('supplier_id')}>
              <option value="">— Select supplier —</option>
              {suppliers.map((supplier) => (
                <option key={supplier.id} value={supplier.id}>
                  {supplier.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="unit_price">
              Unit price (USD)
            </label>
            <input
              id="unit_price"
              type="number"
              step="0.01"
              min="0"
              className="input"
              {...register('unit_price', { valueAsNumber: true })}
            />
            {errors.unit_price && <p className="mt-1 text-xs text-rose-600">{errors.unit_price.message}</p>}
          </div>
          <div>
            <label className="label" htmlFor="cost_price">
              Cost price (USD)
            </label>
            <input
              id="cost_price"
              type="number"
              step="0.01"
              min="0"
              className="input"
              {...register('cost_price', { valueAsNumber: true })}
            />
            {errors.cost_price && <p className="mt-1 text-xs text-rose-600">{errors.cost_price.message}</p>}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="stock_quantity">
              Stock quantity
            </label>
            <input
              id="stock_quantity"
              type="number"
              min="0"
              className="input"
              {...register('stock_quantity', { valueAsNumber: true })}
            />
            {errors.stock_quantity && (
              <p className="mt-1 text-xs text-rose-600">{errors.stock_quantity.message}</p>
            )}
          </div>
          <div>
            <label className="label" htmlFor="reorder_level">
              Reorder level
            </label>
            <input
              id="reorder_level"
              type="number"
              min="0"
              className="input"
              {...register('reorder_level', { valueAsNumber: true })}
            />
            {errors.reorder_level && (
              <p className="mt-1 text-xs text-rose-600">{errors.reorder_level.message}</p>
            )}
          </div>
        </div>
      </form>
    </Modal>
  )
}
