import { createFileRoute } from '@tanstack/react-router'
import {
  Plus,
  Users,
  AlertCircle,
  Activity,
  Search,
  Grid3x3,
  Table2,
} from 'lucide-react'
import { useState, useEffect, useMemo } from 'react'
import { useStore } from '@tanstack/react-store'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { timelineApi } from '@/lib/api-client'
import { authStore } from '@/lib/auth-store'
import { useSubjects } from '@/hooks/useSubjects'
import { useToast } from '@/hooks/useToast'
import { SubjectsTable } from '@/components/subjects/SubjectsTable'
import { SubjectsGrid } from '@/components/subjects/SubjectsGrid'
import { EditSubjectModal } from '@/components/subjects/EditSubjectModal'
import { CreateSubjectModal } from '@/components/subjects/CreateSubjectModal'
import { EmptyState } from '@/components/ui/EmptyState'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { LoadingIcon } from '@/components/ui/icons'
import type { SubjectWithMetadata } from '@/hooks/useSubjects'

export const Route = createFileRoute('/subjects/')({
  component: SubjectsPage,
})

type ViewMode = 'grid' | 'table'

function SubjectsPage() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingSubject, setEditingSubject] = useState<SubjectWithMetadata | null>(null)
  const [filterType, setFilterType] = useState<string>('')
  const [search, setSearch] = useState('')
  // Always start with 'grid' so SSR and first client render match; read localStorage after mount
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [hasMounted, setHasMounted] = useState(false)

  // Subject types from Settings (config); used for filter dropdown and create modal
  const { data: subjectTypesFromApi = [] } = useQuery({
    queryKey: ['subject-types'],
    queryFn: async () => {
      const { data, error } = await timelineApi.subjectTypes.list({
        skip: 0,
        limit: 500,
      })
      if (error) return []
      return Array.isArray(data) ? data : []
    },
  })

  // Get filtered subjects
  const { subjects, isLoading, isError, error } = useSubjects({
    filterType,
    search,
  })

  // Subject type options: from Subject types API only (Settings → Subject types). Used for filter and create modal.
  const subjectTypeOptions = useMemo(
    () =>
      subjectTypesFromApi.map((t) => ({
        type_name: t.type_name,
        display_name: t.display_name || t.type_name,
      })),
    [subjectTypesFromApi]
  )

  // Filter dropdown also includes any type that appears in subject data but has no config (so legacy types are filterable)
  const filterTypeOptions = useMemo(() => {
    const fromConfig = subjectTypeOptions
    const fromData = [...new Set(subjects.map((s) => s.subject_type))]
    const known = new Set(fromConfig.map((t) => t.type_name))
    const extra = fromData.filter((t) => !known.has(t))
    return [
      ...fromConfig,
      ...extra.map((type_name) => ({ type_name, display_name: type_name })),
    ]
  }, [subjectTypeOptions, subjects])

  useEffect(() => {
    setHasMounted(true)
  }, [])

  // After mount: restore view mode from localStorage; then persist changes
  useEffect(() => {
    if (!hasMounted) return
    const saved = localStorage.getItem('subjects-view-mode')
    if (saved === 'table') setViewMode('table')
  }, [hasMounted])

  useEffect(() => {
    if (hasMounted) localStorage.setItem('subjects-view-mode', viewMode)
  }, [hasMounted, viewMode])

  const handleCreateSubject = async (
    subjectType: string,
    externalRef?: string,
    displayName?: string,
    attributes?: Record<string, unknown>
  ) => {
    try {
      const { error: apiError } = await timelineApi.subjects.create({
        subject_type: subjectType,
        external_ref: externalRef || undefined,
        display_name: displayName || undefined,
        attributes: attributes ?? undefined,
      })

      if (apiError) {
        console.error('Failed to create subject:', apiError)
        toast.error('Failed to create', 'Unable to create subject')
        return false
      }

      // Invalidate the subjects query to automatically refetch the latest data
      queryClient.invalidateQueries({ queryKey: ['subjects'] })
      setShowCreateModal(false)
      toast.success('Subject created', `New subject "${subjectType}" created`)
      return true
    } catch (err) {
      console.error('Error creating subject:', err)
      toast.error('Error creating', 'An unexpected error occurred')
      return false
    }
  }

  const handleUpdateSubject = async (
    subjectId: string,
    externalRef?: string,
    displayName?: string,
    attributes?: Record<string, unknown>
  ) => {
    try {
      const { error: apiError } = await timelineApi.subjects.update(subjectId, {
        external_ref: externalRef ?? null,
        display_name: displayName ?? null,
        attributes: attributes ?? null,
      })

      if (apiError) {
        console.error('Failed to update subject:', apiError)
        return false
      }

      // Invalidate the subjects query to automatically refetch the latest data
      queryClient.invalidateQueries({ queryKey: ['subjects'] })
      setShowEditModal(false)
      setEditingSubject(null)
      return true
    } catch (err) {
      console.error('Error updating subject:', err)
      return false
    }
  }

  const handleOpenEditModal = (subject: SubjectWithMetadata) => {
    setEditingSubject(subject)
    setShowEditModal(true)
  }

  const authState = useStore(authStore)

  // Use a single loading UI for both SSR and initial client render to avoid hydration mismatch.
  // After mount, auth state is stable and we can branch on isLoading / user.
  const showLoading =
    !hasMounted || authState.isLoading

  if (showLoading) {
    return (
      <div className="min-h-[calc(100vh-4rem)] bg-background flex items-center justify-center">
        <div className="flex items-center gap-3 text-muted-foreground">
          <Activity className="w-5 h-5 animate-pulse" />
          <span>Loading...</span>
        </div>
      </div>
    )
  }

  if (!authState.user) {
    return null
  }

  return (
    <>
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground mb-1">
              Subjects
            </h1>
            <p className="text-sm text-muted-foreground">
              Manage entities and their event timelines
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* View Mode Toggle */}
            <div className="flex items-center gap-1 bg-muted/50 rounded-none p-1 border border-border/30">
              <Button
                onClick={() => setViewMode('grid')}
                variant={viewMode === 'grid' ? 'primary' : 'ghost'}
                size="sm"
                title="Grid view"
              >
                <Grid3x3 className="w-4 h-4" />
              </Button>
              <Button
                onClick={() => setViewMode('table')}
                variant={viewMode === 'table' ? 'primary' : 'ghost'}
                size="sm"
                title="Table view"
              >
                <Table2 className="w-4 h-4" />
              </Button>
            </div>

            {/* Create Button */}
            <Button
              onClick={() => setShowCreateModal(true)}
              variant="primary"
            >
              <Plus className="w-4 h-4" />
              Subject
            </Button>
          </div>
        </div>

        {/* Filter and Search Controls */}
        <div className="mb-4 flex flex-col lg:flex-row items-start lg:items-center gap-3 lg:gap-4">
          {/* Search Input */}
          <div className="relative w-full lg:w-64 flex-shrink-0">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
            <Input
              type="text"
              placeholder="Search by ID or external ref..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10 pr-4"
            />
          </div>

          {/* Filter Controls */}
          {filterTypeOptions.length > 0 && (
            <div className="w-full lg:w-auto flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-3">
              <label className="text-sm font-medium text-foreground/90 whitespace-nowrap">
                Filter by type:
              </label>
              <div className="flex items-center gap-2 w-full sm:w-auto">
                <Select
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                  className="flex-1 sm:flex-none"
                >
                  <option value="">All types</option>
                  {filterTypeOptions.map(({ type_name, display_name }) => (
                    <option key={type_name} value={type_name}>
                      {display_name}
                    </option>
                  ))}
                </Select>
                {filterType && (
                  <Button
                    onClick={() => setFilterType('')}
                    variant="ghost"
                    size="sm"
                    className="flex-shrink-0"
                  >
                    Clear
                  </Button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Content */}
        {isLoading && (
          <div className="min-h-[300px] flex items-center justify-center">
            <div className="flex items-center gap-3 text-muted-foreground">
              <LoadingIcon />
              <span>Loading subjects...</span>
            </div>
          </div>
        )}

        {isError && (
          <EmptyState
            icon={AlertCircle}
            title="Unable to Load Subjects"
            description={error?.message || 'An unexpected error occurred. Please check your connection and try again.'}
          />
        )}

        {!isLoading && !isError && subjects.length === 0 && (
          <div className="bg-card/80 backdrop-blur-sm rounded-none border border-border/50">
            <EmptyState
              icon={Users}
              title={search || filterType ? 'No subjects match' : 'No subjects yet'}
              description={
                search || filterType
                  ? 'Try adjusting your filters or search terms'
                  : 'Create your first subject to start tracking events and building verifiable event chains'
              }
              action={{
                label: 'Create Subject',
                onClick: () => setShowCreateModal(true),
              }}
              secondaryAction={
                search || filterType
                  ? {
                      label: 'Clear Filters',
                      onClick: () => {
                        setSearch('')
                        setFilterType('')
                      },
                    }
                  : undefined
              }
            />
          </div>
        )}

        {!isLoading && !isError && subjects.length > 0 && (
          viewMode === 'grid' ? (
            <SubjectsGrid
              data={subjects}
              onEdit={handleOpenEditModal}
              subjectTypeConfig={subjectTypesFromApi}
            />
          ) : (
            <SubjectsTable
              data={subjects}
              onEdit={handleOpenEditModal}
              subjectTypeConfig={subjectTypesFromApi}
            />
          )
        )}

        {/* Create Subject Modal */}
        <CreateSubjectModal
          isOpen={showCreateModal}
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreateSubject}
          subjectTypes={subjectTypesFromApi}
          subjectTypeOptions={subjectTypeOptions}
        />

        {/* Edit Subject Modal */}
        {editingSubject && (
          <EditSubjectModal
            isOpen={showEditModal}
            onClose={() => {
              setShowEditModal(false)
              setEditingSubject(null)
            }}
            subject={editingSubject}
            subjectTypes={subjectTypesFromApi}
            onUpdate={handleUpdateSubject}
          />
        )}
    </>
  )
}