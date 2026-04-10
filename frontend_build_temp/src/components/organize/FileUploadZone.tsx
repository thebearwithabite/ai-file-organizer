import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useMutation } from '@tanstack/react-query'
import { Upload, FileUp } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '../../services/api'
import { cn } from '../../lib/utils'

interface FileUploadZoneProps {
  onClassificationComplete: (result: any) => void
}

export default function FileUploadZone({ onClassificationComplete }: FileUploadZoneProps) {
  const { mutate: uploadFile, isPending } = useMutation({
    mutationFn: api.uploadFile,
    onSuccess: (data) => {
      toast.success('File analyzed successfully')
      onClassificationComplete(data)
    },
    onError: (error: any) => {
      toast.error('Upload failed', {
        description: error.message || 'Check that the backend is running',
      })
    },
  })

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      uploadFile(acceptedFiles[0])
    }
  }, [uploadFile])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    disabled: isPending,
  })

  return (
    <div
      {...getRootProps()}
      className={cn(
        "border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-300 cursor-pointer",
        isDragActive
          ? "border-primary bg-primary/10"
          : "border-white/20 hover:border-white/40",
        isPending && "opacity-50 cursor-not-allowed"
      )}
    >
      <input {...getInputProps()} />

      {isPending ? (
        <>
          <div className="text-5xl mb-4 animate-pulse">⏳</div>
          <p className="text-xl text-white/80 mb-2">Analyzing file...</p>
          <p className="text-sm text-white/40">AI is classifying your file</p>
        </>
      ) : isDragActive ? (
        <>
          <FileUp size={48} className="mx-auto mb-4 text-primary" />
          <p className="text-xl text-primary font-semibold">Drop file here</p>
        </>
      ) : (
        <>
          <Upload size={48} className="mx-auto mb-4 text-white/40" />
          <p className="text-xl text-white mb-2 font-semibold">Drag & drop a file here</p>
          <p className="text-sm text-white/60 mb-4">or</p>
          <button className="px-6 py-3 bg-primary hover:bg-primary-hover rounded-lg font-medium transition-colors">
            Browse Files
          </button>
          <p className="text-xs text-white/40 mt-4">
            Supports: PDF, DOCX, Images, Audio, Video, and more
          </p>
        </>
      )}
    </div>
  )
}
