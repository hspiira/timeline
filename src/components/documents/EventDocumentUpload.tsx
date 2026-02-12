import { useState, useRef } from 'react'
import { Upload, X } from 'lucide-react'
import { useToast } from '@/hooks/useToast'
import { LoadingIcon } from '@/components/ui/icons'
import { Button } from '@/components/ui/button'

export interface EventDocumentUploadProps {
  subjectId: string
  onFilesChanged: (files: File[]) => void
  onError?: (error: string) => void
  required?: boolean
}

interface StagedFile {
  id: string
  file: File
}

const MAX_FILE_SIZE = 100 * 1024 * 1024 // 100MB
const ALLOWED_TYPES = [
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  'text/plain',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
]

export function EventDocumentUpload({
  onFilesChanged,
  onError,
}: EventDocumentUploadProps) {
  const [stagedFiles, setStagedFiles] = useState<StagedFile[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const toast = useToast()

  const validateFile = (file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return `File type not supported: ${file.type}`
    }
    if (file.size > MAX_FILE_SIZE) {
      return `File size exceeds 100MB: ${(file.size / 1024 / 1024).toFixed(2)}MB`
    }
    return null
  }


  const handleFiles = (fileList: FileList) => {
    const newFiles: StagedFile[] = []

    Array.from(fileList).forEach((file) => {
      const error = validateFile(file)

      if (error) {
        onError?.(error)
        toast.error('Invalid file', error)
        return
      }

      const stagedFile: StagedFile = {
        id: crypto.randomUUID(),
        file,
      }

      newFiles.push(stagedFile)
    })

    const updated = [...stagedFiles, ...newFiles]
    setStagedFiles(updated)
    onFilesChanged(updated.map((f) => f.file))
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFiles(e.target.files)
    }
  }

  const removeFile = (id: string) => {
    const updated = stagedFiles.filter((f) => f.id !== id)
    setStagedFiles(updated)
    onFilesChanged(updated.map((f) => f.file))
  }

  return (
    <div className="space-y-2.5">

      {/* Upload Area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-xs p-5 text-center transition-colors ${
          isDragging ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          onChange={handleInputChange}
          className="hidden"
          accept={ALLOWED_TYPES.join(',')}
        />

        <div className="space-y-2">
          <Upload className="w-8 h-8 mx-auto text-muted-foreground" />
          <div>
            <p className="font-medium text-foreground text-sm">Drag and drop files here</p>
            <p className="text-xs text-muted-foreground">or click to select files</p>
          </div>
          <p className="text-xs text-muted-foreground">Max 100MB per file. Supported: PDF, images, Word, Excel</p>
        </div>

        <Button
          children={<Upload className="w-4 h-4" />}
          variant="ghost"
          onClick={() => inputRef.current?.click()}
          className="absolute inset-0 opacity-0"
          aria-label="Upload files"
        />
      </div>

      {/* File List */}
      {stagedFiles.length > 0 && (
        <div className="space-y-1.5">
          {stagedFiles.map((stagedFile) => (
            <div key={stagedFile.id} className="flex items-center gap-2.5 p-2.5 bg-card rounded-xs border border-border/50">
              {/* Status Icon */}
              <div className="shrink-0">
                <LoadingIcon size="sm" className="text-primary" />
              </div>

              {/* File Info */}
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate">{stagedFile.file.name}</p>
                <p className="text-xs text-muted-foreground">{(stagedFile.file.size / 1024 / 1024).toFixed(2)}MB</p>
                <p className="text-xs text-muted-foreground italic">Staged - will upload with event</p>
              </div>

              {/* Remove Button */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => removeFile(stagedFile.id)}
                aria-label="Remove file"
              >
                <X className="w-3 h-3" />
              </Button>
            </div>
          ))}

          {/* Status Summary */}
          <p className="text-xs text-blue-600 dark:text-blue-400 font-medium">
            {stagedFiles.length} file{stagedFiles.length !== 1 ? 's' : ''} staged for upload
          </p>
        </div>
      )}
    </div>
  )
}
