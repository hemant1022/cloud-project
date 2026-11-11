export type Role = 'admin' | 'manager' | 'viewer'

export interface AuthUser {
  id: number
  email: string
  role: Role
  is_active: boolean
  created_at?: string
}

export interface Category {
  id: number
  name: string
  description?: string | null
}

export interface Supplier {
  id: number
  name: string
  contact_name?: string | null
  email?: string | null
  phone?: string | null
  country?: string | null
}

export interface Product {
  id: number
  sku: string
  name: string
  description: string | null
  category_id: number | null
  category_name: string | null
  supplier_id: number | null
  supplier_name: string | null
  unit_price: number
  cost_price: number
  stock_quantity: number
  reorder_level: number
  inventory_value: number
  is_low_stock: boolean
  is_out_of_stock: boolean
  deficit: number
  created_at: string
  updated_at: string
}

export interface PaginatedProducts {
  items: Product[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface ProductInput {
  sku: string
  name: string
  description?: string | null
  category_id: number | null
  supplier_id: number | null
  unit_price: number
  cost_price: number
  stock_quantity: number
  reorder_level: number
}

export interface BreakdownItem {
  name: string
  product_count: number
  inventory_value: number
}

export interface StatsSummary {
  total_products: number
  total_units: number
  total_inventory_value: number
  low_stock_count: number
  out_of_stock_count: number
  category_breakdown: BreakdownItem[]
  supplier_breakdown: BreakdownItem[]
}

export interface ProductFilters {
  q?: string
  category_id?: number
  supplier_id?: number
  stock_status?: 'all' | 'low' | 'out' | 'in'
  sort?: string
  order?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

export interface ImportErrorItem {
  row: number
  sku?: string | null
  field?: string | null
  message: string
}

export interface ImportResult {
  total_rows: number
  inserted: number
  updated: number
  failed: number
  requests_created: number
  errors: ImportErrorItem[]
}

export interface CatalogRequest {
  id: number
  kind: 'category' | 'supplier'
  name: string
  status: 'pending' | 'approved' | 'rejected'
  requested_by: number | null
  requested_by_email: string | null
  reviewed_by: number | null
  note: string | null
  created_at: string
  reviewed_at: string | null
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: AuthUser
}
