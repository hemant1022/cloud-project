import axios from 'axios'
import type {
  AuthUser,
  CatalogRequest,
  Category,
  ImportResult,
  LoginResponse,
  PaginatedProducts,
  Product,
  ProductFilters,
  ProductInput,
  StatsSummary,
  Supplier,
} from './types'

export const TOKEN_KEY = 'inventory_token'
export const USER_KEY = 'inventory_user'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  timeout: 20_000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401 && !window.location.pathname.startsWith('/login')) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map((item) => (typeof item?.msg === 'string' ? item.msg : JSON.stringify(item)))
        .join(', ')
    }
    return error.message
  }
  return error instanceof Error ? error.message : 'Unexpected error'
}

export async function loginRequest(email: string, password: string): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/login', { email, password })
  return data
}

export async function fetchMe(): Promise<AuthUser> {
  const { data } = await api.get<AuthUser>('/auth/me')
  return data
}

export async function fetchProducts(filters: ProductFilters): Promise<PaginatedProducts> {
  const { data } = await api.get<PaginatedProducts>('/products', { params: filters })
  return data
}

export async function fetchProduct(id: number): Promise<Product> {
  const { data } = await api.get<Product>(`/products/${id}`)
  return data
}

export async function createProduct(payload: ProductInput): Promise<Product> {
  const { data } = await api.post<Product>('/products', payload)
  return data
}

export async function updateProduct(id: number, payload: Partial<ProductInput>): Promise<Product> {
  const { data } = await api.patch<Product>(`/products/${id}`, payload)
  return data
}

export async function deleteProduct(id: number): Promise<void> {
  await api.delete(`/products/${id}`)
}

export async function adjustStock(
  id: number,
  changeQty: number,
  reason: 'RESTOCK' | 'SALE' | 'ADJUSTMENT',
  note?: string,
): Promise<Product> {
  const { data } = await api.post<Product>(`/products/${id}/adjust`, {
    change_qty: changeQty,
    reason,
    note,
  })
  return data
}

export async function fetchSummary(): Promise<StatsSummary> {
  const { data } = await api.get<StatsSummary>('/stats/summary')
  return data
}

export async function fetchLowStock(): Promise<Product[]> {
  const { data } = await api.get<Product[]>('/alerts/low-stock', { params: { include_out_of_stock: true } })
  return data
}

export async function fetchCategories(): Promise<Category[]> {
  const { data } = await api.get<Category[]>('/categories')
  return data
}

export async function fetchSuppliers(): Promise<Supplier[]> {
  const { data } = await api.get<Supplier[]>('/suppliers')
  return data
}

export async function createCategory(name: string, description?: string): Promise<Category> {
  const { data } = await api.post<Category>('/categories', { name, description })
  return data
}

export async function createSupplier(name: string, country?: string): Promise<Supplier> {
  const { data } = await api.post<Supplier>('/suppliers', { name, country })
  return data
}

export async function deleteCategory(id: number): Promise<void> {
  await api.delete(`/categories/${id}`)
}

export async function deleteSupplier(id: number): Promise<void> {
  await api.delete(`/suppliers/${id}`)
}

export async function importProductsCsv(file: File, createMissing: boolean): Promise<ImportResult> {
  const form = new FormData()
  form.append('file', file)
  form.append('create_missing', String(createMissing))
  const { data } = await api.post<ImportResult>('/import', form)
  return data
}

export async function downloadTemplate(): Promise<void> {
  const response = await api.get('/import/template', { responseType: 'blob' })
  const url = URL.createObjectURL(response.data as Blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'inventory-template.csv'
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export async function fetchCatalogRequests(status = 'pending'): Promise<CatalogRequest[]> {
  const { data } = await api.get<CatalogRequest[]>('/catalog-requests', { params: { status } })
  return data
}

export async function approveCatalogRequest(id: number): Promise<CatalogRequest> {
  const { data } = await api.post<CatalogRequest>(`/catalog-requests/${id}/approve`)
  return data
}

export async function rejectCatalogRequest(id: number): Promise<CatalogRequest> {
  const { data } = await api.post<CatalogRequest>(`/catalog-requests/${id}/reject`)
  return data
}
