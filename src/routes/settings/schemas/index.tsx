import { createFileRoute } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { timelineApi } from '@/lib/api-client'
import { Plus, Eye, Trash2, CheckCircle } from 'lucide-react'
import { SchemaFormModal } from '@/components/schemas/SchemaFormModal'
import { ErrorModal } from '@/components/ui/ErrorModal'
import { SchemaViewModal } from '@/components/schemas/SchemaViewModal'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import { DataTable } from '@/components/ui/DataTable'
import type { components } from '@/lib/timeline-api'
import { Button } from '@/components/ui/button'

export const Route = createFileRoute('/settings/schemas/')({
  component: SchemasPage,
})

type SchemaListItem = components['schemas']['EventSchemaListItem']
type SchemaFull = components['schemas']['EventSchemaResponse']

function SchemasPage() {
  const authState = useRequireAuth()
  const [schemas, setSchemas] = useState<SchemaListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [viewingSchema, setViewingSchema] = useState<SchemaFull | null>(null)
  const [loadingSchema, setLoadingSchema] = useState(false)
  const [deletingSchema, setDeletingSchema] = useState<SchemaListItem | null>(null)
  const [subjectTypes, setSubjectTypes] = useState<{ type_name: string; display_name: string }[]>([])

  useEffect(() => {
    if (authState.user) {
      fetchSchemas()
    }
  }, [authState.user])

  useEffect(() => {
    if (authState.user && showCreateModal) {
      timelineApi.subjectTypes.list({ limit: 500 }).then(({ data }) => {
        const list = Array.isArray(data) ? data : []
        setSubjectTypes(list.map((t) => ({ type_name: t.type_name, display_name: t.display_name ?? t.type_name })))
      })
    }
  }, [authState.user, showCreateModal])

  const fetchSchemas = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data, error: apiError } = await timelineApi.eventSchemas.list({
        skip: 0,
        limit: 500,
      })
      if (apiError) {
        setError('Failed to load schemas')
        return
      }
      setSchemas(Array.isArray(data) ? data : [])
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unexpected error loading schemas'
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateSchema = async (
    eventType: string,
    definition: Record<string, any>,
    allowedSubjectTypes?: string[] | null
  ) => {
    try {
      const { data, error: apiError } = await timelineApi.eventSchemas.create({
        event_type: eventType,
        schema_definition: definition,
        is_active: true,
        allowed_subject_types:
          allowedSubjectTypes?.length ? allowedSubjectTypes : undefined,
      })

      if (apiError) {
        const errorMsg =
          typeof apiError === 'object' && 'message' in apiError
            ? (apiError as any).message
            : 'Failed to create schema'
        setError(errorMsg)
        return false
      }

      if (data) {
        const { schema_definition: _, ...listItem } = data
        setSchemas((prev) => [listItem, ...prev])
        setShowCreateModal(false)
        return true
      }
      return false
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unexpected error creating schema'
      setError(errorMsg)
      return false
    }
  }

  const handleDeleteSchema = (schema: SchemaListItem) => {
    setDeletingSchema(schema)
  }

  const handleConfirmDelete = async () => {
    if (!deletingSchema) return

    try {
      const { error: apiError } = await timelineApi.eventSchemas.delete(deletingSchema.id)

      if (apiError) {
        const errorMsg =
          typeof apiError === 'object' && 'detail' in apiError
            ? (apiError as any).detail
            : typeof apiError === 'object' && 'message' in apiError
              ? (apiError as any).message
              : 'Failed to delete schema'
        throw new Error(errorMsg)
      }

      setSchemas((prev) => prev.filter((s) => s.id !== deletingSchema.id))
      setDeletingSchema(null)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to delete schema'
      setError(errorMsg)
      throw err
    }
  }

  if (!authState.user) {
    return null
  }

  // Define columns for DataTable
  const columns: ColumnDef<SchemaListItem>[] = [
    {
      accessorKey: 'event_type',
      header: 'Event Type',
      cell: ({ row }) => (
        <span className="font-medium text-foreground">{row.original.event_type}</span>
      ),
    },
    {
      accessorKey: 'version',
      header: 'Version',
      cell: ({ row }) => (
        <span className="text-muted-foreground">v{row.original.version}</span>
      ),
    },
    {
      id: 'status',
      header: 'Status',
      cell: ({ row }) =>
        row.original.is_active ? (
          <div className="flex items-center gap-1 text-green-600 dark:text-green-400">
            <CheckCircle className="w-3 h-3" />
            <span className="text-xs">Active</span>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">Inactive</span>
        ),
    },
    {
      id: 'created_by',
      header: 'Created By',
      cell: ({ row }) => (
        <span className="text-muted-foreground text-sm">
          {row.original.created_by || '—'}
        </span>
      ),
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => (
        <div className="flex items-center justify-end gap-1">
          <Button
            onClick={async () => {
              setLoadingSchema(true)
              try {
                const { data } = await timelineApi.eventSchemas.get(row.original.id)
                if (data) setViewingSchema(data)
              } catch {
                setError('Failed to load schema details')
              } finally {
                setLoadingSchema(false)
              }
            }}
            disabled={loadingSchema}
            variant="ghost"
            size="sm"
            title="View Schema"
          >
            <Eye className="w-4 h-4" />
          </Button>
          <Button
            onClick={() => handleDeleteSchema(row.original)}
            variant="ghost"
            size="sm"
            title="Delete"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      ),
    },
  ]

  return (
    <>
      {/* Create Schema Modal */}
      {showCreateModal && (
        <SchemaFormModal
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateSchema}
          title="Create Event Schema"
          subjectTypes={subjectTypes}
        />
      )}

      {/* View/Edit Schema Modal */}
      {viewingSchema && <SchemaViewModal schema={viewingSchema} onClose={() => setViewingSchema(null)} />}

      {/* Delete Schema Modal */}
      {deletingSchema && (
        <ConfirmModal
          isOpen={true}
          onClose={() => setDeletingSchema(null)}
          title="Delete Event Schema?"
          message="This action cannot be undone."
          confirmText="Confirm deletion"
          cancelText="Cancel"
          isDestructive={true}
          details={{
            'event type': deletingSchema.event_type,
            'version': `v${deletingSchema.version}`,
            'status': deletingSchema.is_active ? 'Active' : 'Inactive',
          }}
          warning="Deletion is only possible if no events reference this schema version. If you see an error, keep this version as an inactive schema for historical verification."
          onConfirm={handleConfirmDelete}
        />
      )}

      <ErrorModal
        open={!!error}
        onClose={() => setError(null)}
        title="Error"
        message={error ?? ''}
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <h1 className="text-lg font-bold text-foreground">Event Schemas</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Manage JSON schemas for event validation</p>
        </div>
        <Button
          onClick={() => setShowCreateModal(true)}
          variant="primary"
          size="md"
        >
          <Plus className="w-4 h-4" />
          Schema
        </Button>
      </div>

      {/* Schemas Table */}
      <DataTable
        data={schemas}
        columns={columns}
        isLoading={loading}
        isEmpty={schemas.length === 0}
        compact={true}
        enablePagination={true}
        pageSize={10}
        emptyState={{
          title: 'No schemas yet',
          description: 'Create your first event schema to enable validation',
          action: (
            <Button onClick={() => setShowCreateModal(true)} variant="primary" size="md">
              <Plus className="w-4 h-4" />
              Schema
            </Button>
          ),
        }}
      />
    </>
  )
}
