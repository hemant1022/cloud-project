import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Alerts from './pages/Alerts'
import Approvals from './pages/Approvals'
import Catalog from './pages/Catalog'
import Dashboard from './pages/Dashboard'
import Import from './pages/Import'
import Login from './pages/Login'
import Products from './pages/Products'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="products" element={<Products />} />
        <Route path="alerts" element={<Alerts />} />
        <Route
          path="import"
          element={
            <ProtectedRoute roles={['admin', 'manager']}>
              <Import />
            </ProtectedRoute>
          }
        />
        <Route
          path="approvals"
          element={
            <ProtectedRoute roles={['admin']}>
              <Approvals />
            </ProtectedRoute>
          }
        />
        <Route
          path="catalog"
          element={
            <ProtectedRoute roles={['admin', 'manager']}>
              <Catalog />
            </ProtectedRoute>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
