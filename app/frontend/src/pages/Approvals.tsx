import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, X } from 'lucide-react'
import { useState } from 'react'
import {
  apiErrorMessage,
  approveCatalogRequest,
  fetchCatalogRequests,
  rejectCatalogRequest,
} from '../api'
import { Badge, EmptyState, ErrorBanner, PageHeader, Spinner, SuccessBanner } from '../components/ui'
import { dateTime } from '../lib/format'

export default function Approvals() {
  const queryClient = useQueryClient()
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const requestsQuery = useQuery({
    queryKey: ['catalog-requests', 'pending'],
    queryFn: () => fetchCatalogRequests('pending'),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['catalog-requests'] })
    queryClient.invalidateQueries({ queryKey: ['categories'] })
    queryClient.invalidateQueries({ queryKey: ['suppliers'] })
  }

  const approveMutation = useMutation({ mutationFn: approveCatalogRequest, onSuccess: invalidate })
  const rejectMutation = useMutation({ mutationFn: rejectCatalogRequest, onSuccess: invalidate })

  const handleApprove = async (id: number, name: string) => {
    setMessage(null)
    setError(null)
    try {
      await approveMutation.mutateAsync(id)
      setMessage(`Approved "${name}". It is now available for CSV imports.`)
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

  const handleReject = async (id: number, name: string) => {
    setMessage(null)
    setError(null)
    try {
      await rejectMutation.mutateAsync(id)
      setMessage(`Rejected "${name}".`)
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

  const requests = requestsQuery.data ?? []
  const busy = approveMutation.isPending || rejectMutation.isPending

  return (
    <div>
      <PageHeader
        title="Catalog approvals"
        subtitle="Approve new categories and suppliers requested during CSV imports."
      />

      <div className="mb-4 space-y-3">
        <SuccessBanner message={message} />
        <ErrorBanner message={error} />
      </div>

      <div className="card overflow-hidden">
        {requestsQuery.isLoading ? (
          <Spinner label="Loading requests…" />
        ) : requestsQuery.error ? (
          <div className="p-4">
            <ErrorBanner message={apiErrorMessage(requestsQuery.error)} />
          </div>
        ) : requests.length === 0 ? (
          <EmptyState
            title="No pending requests"
            description="When a CSV references a new category or supplier, it will appear here for approval."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="table-head">
                <tr>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Requested by</th>
                  <th className="px-4 py-3">Requested at</th>
                  <th className="px-4 py-3">Note</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {requests.map((request) => (
                  <tr key={request.id} className="hover:bg-slate-50/60">
                    <td className="px-4 py-3">
                      <Badge tone={request.kind === 'category' ? 'blue' : 'brand'}>{request.kind}</Badge>
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-900">{request.name}</td>
                    <td className="px-4 py-3 text-slate-600">{request.requested_by_email ?? '—'}</td>
                    <td className="px-4 py-3 text-slate-600">{dateTime(request.created_at)}</td>
                    <td className="max-w-xs px-4 py-3 text-slate-500">{request.note ?? '—'}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          className="btn-primary"
                          disabled={busy}
                          onClick={() => handleApprove(request.id, request.name)}
                        >
                          <Check className="h-4 w-4" />
                          Approve
                        </button>
                        <button
                          type="button"
                          className="btn-danger"
                          disabled={busy}
                          onClick={() => handleReject(request.id, request.name)}
                        >
                          <X className="h-4 w-4" />
                          Reject
                        </button>
                      </div>
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
