import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, CheckCircle2, Download, FileSpreadsheet, Upload } from 'lucide-react'
import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { apiErrorMessage, downloadTemplate, importProductsCsv } from '../api'
import { useAuth } from '../auth/AuthContext'
import { ErrorBanner, PageHeader } from '../components/ui'
import { number } from '../lib/format'
import type { ImportResult } from '../types'

export default function Import() {
  const { hasRole } = useAuth()
  const isAdmin = hasRole('admin')
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [createMissing, setCreateMissing] = useState(false)
  const [templateError, setTemplateError] = useState<string | null>(null)
  const [localError, setLocalError] = useState<string | null>(null)
  const [result, setResult] = useState<ImportResult | null>(null)

  const importMutation = useMutation({ mutationFn: (payload: { file: File; createMissing: boolean }) =>
    importProductsCsv(payload.file, payload.createMissing),
  })

  const onDrop = useCallback((accepted: File[]) => {
    setLocalError(null)
    setResult(null)
    importMutation.reset()
    const next = accepted[0] ?? null
    if (next && !next.name.toLowerCase().endsWith('.csv')) {
      setLocalError('Please select a .csv file.')
      setFile(null)
      return
    }
    setFile(next)
  }, [importMutation])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/csv': ['.csv'] },
    maxFiles: 1,
  })

  const handleTemplate = async () => {
    setTemplateError(null)
    try {
      await downloadTemplate()
    } catch (error) {
      setTemplateError(apiErrorMessage(error))
    }
  }

  const handleImport = async () => {
    if (!file) {
      setLocalError('Choose a CSV file first.')
      return
    }
    setLocalError(null)
    setResult(null)
    try {
      const data = await importMutation.mutateAsync({ file, createMissing })
      setResult(data)
      queryClient.invalidateQueries({ queryKey: ['products'] })
      queryClient.invalidateQueries({ queryKey: ['summary'] })
      queryClient.invalidateQueries({ queryKey: ['low-stock'] })
      queryClient.invalidateQueries({ queryKey: ['catalog-requests'] })
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      queryClient.invalidateQueries({ queryKey: ['suppliers'] })
    } catch {
      // handled by importMutation.error
    }
  }

  return (
    <div>
      <PageHeader
        title="Import products"
        subtitle="Bulk-load inventory from CSV. Unknown categories or suppliers require admin approval."
        actions={
          <button type="button" className="btn-secondary" onClick={handleTemplate}>
            <Download className="h-4 w-4" />
            Download template
          </button>
        }
      />

      <div className="space-y-3">
        <ErrorBanner message={templateError} />
        <ErrorBanner message={localError} />
        <ErrorBanner message={importMutation.error ? apiErrorMessage(importMutation.error) : null} />
      </div>

      <div className="mt-4 grid gap-6 lg:grid-cols-3">
        <div className="card p-5 lg:col-span-2">
          <div
            {...getRootProps()}
            className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-14 text-center transition ${
              isDragActive ? 'border-brand-500 bg-brand-50' : 'border-slate-300 bg-slate-50/60 hover:border-brand-400'
            }`}
          >
            <input {...getInputProps()} />
            <span className="rounded-full bg-white p-3 text-brand-600 shadow-sm">
              <Upload className="h-6 w-6" />
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-800">
                {isDragActive ? 'Drop the CSV here' : 'Drag and drop a CSV, or click to browse'}
              </p>
              <p className="mt-1 text-xs text-slate-500">Maximum 5 MB · up to 10,000 rows</p>
            </div>
            {file && (
              <div className="mt-2 inline-flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-sm text-slate-700 shadow-sm">
                <FileSpreadsheet className="h-4 w-4 text-emerald-600" />
                <span className="max-w-xs truncate">{file.name}</span>
                <span className="text-xs text-slate-400">{Math.ceil(file.size / 1024)} KB</span>
              </div>
            )}
          </div>

          <div className="mt-5 space-y-4">
            {isAdmin && (
              <label className="flex items-start gap-3 rounded-lg border border-slate-200 p-3 text-sm">
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                  checked={createMissing}
                  onChange={(event) => setCreateMissing(event.target.checked)}
                />
                <span>
                  <span className="block font-medium text-slate-800">
                    Create missing categories and suppliers automatically
                  </span>
                  <span className="text-xs text-slate-500">
                    Admin-only. Managers can import existing catalog values; new ones are queued for approval.
                  </span>
                </span>
              </label>
            )}

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="btn-primary"
                onClick={handleImport}
                disabled={!file || importMutation.isPending}
              >
                <Upload className="h-4 w-4" />
                {importMutation.isPending ? 'Importing…' : 'Import CSV'}
              </button>
              {file && (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setFile(null)
                    setResult(null)
                    importMutation.reset()
                  }}
                >
                  Clear
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="card p-5">
          <h2 className="text-sm font-semibold text-slate-900">How approval works</h2>
          <ol className="mt-3 space-y-3 text-sm text-slate-600">
            <li>1. Managers upload a CSV with existing category and supplier names.</li>
            <li>2. Rows referencing unknown values are rejected and queued as approval requests.</li>
            <li>3. An admin approves the request on the Approvals page.</li>
            <li>4. Re-upload the same CSV; the rows now import successfully.</li>
          </ol>
          <p className="mt-4 rounded-lg bg-slate-50 p-3 text-xs text-slate-500">
            Required columns: sku, name, category, supplier, unit_price, stock_quantity, reorder_level.
            Optional: description, cost_price.
          </p>
        </div>
      </div>

      {result && (
        <div className="card mt-6 p-5">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            <h2 className="text-sm font-semibold text-slate-900">Import summary</h2>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-5">
            {[
              ['Total rows', result.total_rows],
              ['Inserted', result.inserted],
              ['Updated', result.updated],
              ['Failed', result.failed],
              ['Requests', result.requests_created],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg bg-slate-50 p-3 text-center">
                <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
                <p className="mt-1 text-lg font-semibold text-slate-900">{number(Number(value))}</p>
              </div>
            ))}
          </div>

          {result.requests_created > 0 && (
            <p className="mt-4 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              {result.requests_created} new catalog request(s) were created. An admin must approve them before
              those rows can be imported.
            </p>
          )}

          {result.errors.length > 0 && (
            <div className="mt-4 overflow-hidden rounded-lg border border-slate-200">
              <table className="min-w-full text-sm">
                <thead className="table-head">
                  <tr>
                    <th className="px-3 py-2">Row</th>
                    <th className="px-3 py-2">SKU</th>
                    <th className="px-3 py-2">Error</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {result.errors.map((item, index) => (
                    <tr key={`${item.row}-${index}`}>
                      <td className="px-3 py-2 text-slate-600">{item.row}</td>
                      <td className="px-3 py-2 text-slate-600">{item.sku ?? '—'}</td>
                      <td className="px-3 py-2 text-rose-600">{item.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
