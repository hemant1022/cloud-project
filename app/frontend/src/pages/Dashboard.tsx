import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, DollarSign, Package, ShoppingCart, XCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { apiErrorMessage, fetchLowStock, fetchSummary } from '../api'
import { Badge, ErrorBanner, KpiCard, PageHeader, Spinner } from '../components/ui'
import { currency, number } from '../lib/format'

const PIE_COLORS = ['#10b981', '#f59e0b', '#ef4444']

export default function Dashboard() {
  const summaryQuery = useQuery({ queryKey: ['summary'], queryFn: fetchSummary })
  const lowStockQuery = useQuery({ queryKey: ['low-stock'], queryFn: fetchLowStock })

  if (summaryQuery.isLoading) return <Spinner label="Loading dashboard…" />

  if (summaryQuery.error) {
    return (
      <div>
        <PageHeader title="Dashboard" />
        <ErrorBanner message={apiErrorMessage(summaryQuery.error)} />
      </div>
    )
  }

  const summary = summaryQuery.data!
  const healthy = Math.max(summary.total_products - summary.low_stock_count - summary.out_of_stock_count, 0)
  const pieData = [
    { name: 'Healthy', value: healthy },
    { name: 'Low stock', value: summary.low_stock_count },
    { name: 'Out of stock', value: summary.out_of_stock_count },
  ]
  const categoryData = summary.category_breakdown.slice(0, 6).map((item) => ({
    name: item.name,
    value: item.inventory_value,
    products: item.product_count,
  }))
  const lowStock = (lowStockQuery.data ?? []).slice(0, 5)

  return (
    <div>
      <PageHeader
        title="Inventory dashboard"
        subtitle="Live view of inventory value, stock health, and products that need attention."
        actions={
          <Link to="/products" className="btn-primary">
            <Package className="h-4 w-4" />
            Manage products
          </Link>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Total inventory value"
          value={currency(summary.total_inventory_value)}
          hint={`${number(summary.total_units)} units on hand`}
          icon={<DollarSign className="h-5 w-5" />}
          accent="brand"
        />
        <KpiCard
          label="Products"
          value={number(summary.total_products)}
          hint={`${summary.category_breakdown.length} categories`}
          icon={<Package className="h-5 w-5" />}
          accent="blue"
        />
        <KpiCard
          label="Low stock"
          value={number(summary.low_stock_count)}
          hint="At or below reorder level"
          icon={<AlertTriangle className="h-5 w-5" />}
          accent="amber"
        />
        <KpiCard
          label="Out of stock"
          value={number(summary.out_of_stock_count)}
          hint="Requires immediate restock"
          icon={<XCircle className="h-5 w-5" />}
          accent="red"
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="card p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Inventory value by category</h2>
              <p className="text-xs text-slate-500">Top categories by stock value</p>
            </div>
          </div>
          {categoryData.length === 0 ? (
            <p className="py-10 text-center text-sm text-slate-500">No products yet.</p>
          ) : (
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryData} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-15} height={50} textAnchor="end" />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(value) => `$${Math.round(Number(value) / 1000)}k`} />
                  <Tooltip formatter={(value) => currency(Number(value))} />
                  <Bar dataKey="value" fill="#4f46e5" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="card p-5">
          <h2 className="text-sm font-semibold text-slate-900">Stock health</h2>
          <p className="text-xs text-slate-500">Products by stock status</p>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={3}>
                  {pieData.map((entry, index) => (
                    <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => number(Number(value))} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="card mt-6 overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Needs attention</h2>
            <p className="text-xs text-slate-500">Five most urgent low-stock products</p>
          </div>
          <Link to="/alerts" className="text-sm font-medium text-brand-600 hover:text-brand-700">
            View all alerts
          </Link>
        </div>

        {lowStockQuery.isLoading ? (
          <Spinner label="Loading alerts…" />
        ) : lowStock.length === 0 ? (
          <p className="px-5 py-10 text-center text-sm text-slate-500">Nothing needs restocking right now.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="table-head">
                <tr>
                  <th className="px-5 py-3">Product</th>
                  <th className="px-5 py-3">Category</th>
                  <th className="px-5 py-3 text-right">Stock</th>
                  <th className="px-5 py-3 text-right">Reorder at</th>
                  <th className="px-5 py-3 text-right">Deficit</th>
                  <th className="px-5 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {lowStock.map((product) => (
                  <tr key={product.id}>
                    <td className="px-5 py-3">
                      <p className="font-medium text-slate-900">{product.name}</p>
                      <p className="text-xs text-slate-500">{product.sku}</p>
                    </td>
                    <td className="px-5 py-3 text-slate-600">{product.category_name ?? '—'}</td>
                    <td className="px-5 py-3 text-right font-medium">{number(product.stock_quantity)}</td>
                    <td className="px-5 py-3 text-right text-slate-600">{number(product.reorder_level)}</td>
                    <td className="px-5 py-3 text-right font-medium text-rose-600">{number(product.deficit)}</td>
                    <td className="px-5 py-3">
                      {product.is_out_of_stock ? (
                        <Badge tone="red">
                          <XCircle className="h-3 w-3" /> Out
                        </Badge>
                      ) : (
                        <Badge tone="amber">
                          <ShoppingCart className="h-3 w-3" /> Low
                        </Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
