import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'CSV Processor',
  description: 'Upload and process CSV files',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}

