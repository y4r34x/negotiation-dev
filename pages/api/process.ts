import { IncomingMessage, ServerResponse } from 'http'
import { Readable } from 'stream'

// FastAPI backend URL
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

// Disable body parsing - we'll stream the request directly
export const config = {
  api: {
    bodyParser: false,
  },
}

// Helper to convert IncomingMessage to Readable stream
function streamToBuffer(stream: Readable): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = []
    stream.on('data', (chunk) => chunks.push(chunk))
    stream.on('end', () => resolve(Buffer.concat(chunks)))
    stream.on('error', reject)
  })
}

// Default export handler
export default async function handler(
  req: IncomingMessage,
  res: ServerResponse
) {
  // Only allow POST requests
  if (req.method !== 'POST') {
    res.statusCode = 405
    res.setHeader('Content-Type', 'application/json')
    res.end(JSON.stringify({ detail: 'Method not allowed' }))
    return
  }

  try {
    // Get the content-type header to preserve multipart boundary
    const contentType = req.headers['content-type'] || 'multipart/form-data'
    
    // Read the entire request body
    const bodyBuffer = await streamToBuffer(req)

    // Forward to FastAPI backend with the same headers
    const backendResponse = await fetch(`${BACKEND_URL}/process`, {
      method: 'POST',
      headers: {
        'Content-Type': contentType,
        'Content-Length': bodyBuffer.length.toString(),
      },
      body: bodyBuffer,
    })

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({
        detail: 'Backend error occurred',
      }))
      res.statusCode = backendResponse.status
      res.setHeader('Content-Type', 'application/json')
      res.end(JSON.stringify({ detail: errorData.detail || 'Backend processing failed' }))
      return
    }

    // Get the response content type from backend
    const responseContentType = backendResponse.headers.get('content-type') || 'text/csv'
    
    // Get the response as a buffer
    const buffer = Buffer.from(await backendResponse.arrayBuffer())

    // Pipe response directly back to client with same Content-Type
    res.statusCode = 200
    res.setHeader('Content-Type', responseContentType)
    
    // Copy other relevant headers from backend
    const contentDisposition = backendResponse.headers.get('content-disposition')
    if (contentDisposition) {
      res.setHeader('Content-Disposition', contentDisposition)
    }

    res.end(buffer)
  } catch (error) {
    console.error('Error processing file:', error)
    const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred'
    const errorStack = error instanceof Error ? error.stack : undefined
    
    // Log full error details for debugging
    console.error('Full error details:', {
      message: errorMessage,
      stack: errorStack,
      error: error,
    })
    
    res.statusCode = 500
    res.setHeader('Content-Type', 'application/json')
    res.end(
      JSON.stringify({
        detail: errorMessage,
      })
    )
  }
}

