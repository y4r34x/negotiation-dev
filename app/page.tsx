'use client'

import { useState, FormEvent, ChangeEvent, useRef, DragEvent } from 'react'

export default function Home() {
  const [file, setFile] = useState<File | null>(null)
  const [status, setStatus] = useState<string>('')
  const [error, setError] = useState<string>('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateFile = (selectedFile: File): boolean => {
    return selectedFile.type === 'text/csv' || selectedFile.name.endsWith('.csv')
  }

  const handleFileSelect = (selectedFile: File) => {
    if (validateFile(selectedFile)) {
      setFile(selectedFile)
      setError('')
      setStatus('')
    } else {
      setError('Please select a CSV file')
      setFile(null)
    }
  }

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      handleFileSelect(selectedFile)
    }
  }

  const handleDragEnter = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const droppedFile = e.dataTransfer.files?.[0]
    if (droppedFile) {
      handleFileSelect(droppedFile)
    }
  }

  const handleDropZoneClick = () => {
    fileInputRef.current?.click()
  }

  const handleSearch = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    
    if (!file) {
      setError('Please select a file first')
      return
    }

    setIsProcessing(true)
    setError('')
    setStatus('Uploading and processing...')

    try {
      // Create FormData
      const formData = new FormData()
      formData.append('file', file)

      // POST to API route with timeout
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 300000) // 5 minute timeout
      
      const response = await fetch('/api/process', {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      })
      
      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error occurred' }))
        throw new Error(errorData.detail || `Server error: ${response.status}`)
      }

      setStatus('Searching and processing...')

      // Get the response as a Blob
      const blob = await response.blob()

      // Extract filename from Content-Disposition header if available
      const contentDisposition = response.headers.get('content-disposition')
      let filename = 'output.csv'
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '')
        }
      }

      // Trigger browser download
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      setStatus('Download complete!')
      setIsProcessing(false)
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        setError('Request timed out. The file may be too large or the search is taking too long.')
      } else {
        setError(err instanceof Error ? err.message : 'An error occurred while processing the file')
      }
      setStatus('')
      setIsProcessing(false)
    }
  }

  return (
    <main style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '12px',
        padding: '2.5rem',
        boxShadow: '0 10px 40px rgba(0, 0, 0, 0.15)',
        maxWidth: '600px',
        width: '100%',
      }}>
        <h1 style={{
          marginBottom: '0.5rem',
          fontSize: '2rem',
          fontWeight: '700',
          textAlign: 'center',
          color: '#1f2937',
        }}>
          CSV Search Processor
        </h1>
        <p style={{
          marginBottom: '2rem',
          fontSize: '0.875rem',
          textAlign: 'center',
          color: '#6b7280',
        }}>
          Upload a CSV file with search_terms column to process
        </p>

        <form onSubmit={handleSearch}>
          <div 
            onClick={handleDropZoneClick}
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            style={{
              marginBottom: '1.5rem',
              border: `2px dashed ${isDragging ? '#3b82f6' : '#d1d5db'}`,
              borderRadius: '8px',
              padding: '3rem 2rem',
              textAlign: 'center',
              cursor: isProcessing ? 'not-allowed' : 'pointer',
              backgroundColor: isDragging ? '#eff6ff' : '#f9fafb',
              transition: 'all 0.2s ease',
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              onChange={handleFileChange}
              disabled={isProcessing}
              style={{ display: 'none' }}
            />
            
            {!file ? (
              <>
                <div style={{
                  fontSize: '3rem',
                  marginBottom: '1rem',
                }}>
                  📄
                </div>
                <p style={{
                  fontSize: '1rem',
                  fontWeight: '500',
                  color: '#374151',
                  marginBottom: '0.5rem',
                }}>
                  {isDragging ? 'Drop your CSV file here' : 'Drag & drop your CSV file here'}
                </p>
                <p style={{
                  fontSize: '0.875rem',
                  color: '#6b7280',
                }}>
                  or click to browse
                </p>
              </>
            ) : (
              <>
                <div style={{
                  fontSize: '2.5rem',
                  marginBottom: '1rem',
                }}>
                  ✓
                </div>
                <p style={{
                  fontSize: '1rem',
                  fontWeight: '500',
                  color: '#10b981',
                  marginBottom: '0.5rem',
                }}>
                  {file.name}
                </p>
                <p style={{
                  fontSize: '0.875rem',
                  color: '#6b7280',
                }}>
                  Click to select a different file
                </p>
              </>
            )}
          </div>

          <button
            type="submit"
            disabled={!file || isProcessing}
            style={{
              width: '100%',
              padding: '0.875rem',
              backgroundColor: isProcessing || !file ? '#9ca3af' : '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '1rem',
              fontWeight: '600',
              cursor: isProcessing || !file ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s ease',
              boxShadow: isProcessing || !file ? 'none' : '0 4px 6px rgba(59, 130, 246, 0.3)',
            }}
            onMouseEnter={(e) => {
              if (!isProcessing && file) {
                e.currentTarget.style.backgroundColor = '#2563eb'
                e.currentTarget.style.transform = 'translateY(-1px)'
                e.currentTarget.style.boxShadow = '0 6px 12px rgba(59, 130, 246, 0.4)'
              }
            }}
            onMouseLeave={(e) => {
              if (!isProcessing && file) {
                e.currentTarget.style.backgroundColor = '#3b82f6'
                e.currentTarget.style.transform = 'translateY(0)'
                e.currentTarget.style.boxShadow = '0 4px 6px rgba(59, 130, 246, 0.3)'
              }
            }}
          >
            {isProcessing ? 'Searching...' : 'Search'}
          </button>
        </form>

        {status && (
          <div style={{
            marginTop: '1rem',
            padding: '0.75rem',
            backgroundColor: '#dbeafe',
            color: '#1e40af',
            borderRadius: '4px',
            fontSize: '0.875rem',
            textAlign: 'center',
          }}>
            {status}
          </div>
        )}

        {error && (
          <div style={{
            marginTop: '1rem',
            padding: '0.75rem',
            backgroundColor: '#fee2e2',
            color: '#991b1b',
            borderRadius: '4px',
            fontSize: '0.875rem',
            textAlign: 'center',
          }}>
            Error: {error}
          </div>
        )}
      </div>
    </main>
  )
}

