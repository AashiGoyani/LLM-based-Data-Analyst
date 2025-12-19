'use client'

import { useState } from 'react'
import dynamic from 'next/dynamic'

// Dynamically import Plotly to avoid SSR issues
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false })

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface QueryResult {
  sql: string
  data: any[]
  columns: string[]
  row_count: number
  chart?: string
  chart_type?: string
  error?: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  result?: QueryResult
}

export default function Home() {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)

  const exampleQueries = [
    'Show the average trip distance by payment type',
    'What is the monthly revenue trend for 2016?',
    'Show the top 10 days with highest total revenue',
    'What is the average tip percentage by rate code?',
  ]

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim() || loading) return

    const userMessage: Message = {
      role: 'user',
      content: query.trim(),
    }

    setMessages((prev) => [...prev, userMessage])
    setQuery('')
    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: userMessage.content,
          generate_chart: true,
        }),
      })

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`)
      }

      const result: QueryResult = await response.json()

      const assistantMessage: Message = {
        role: 'assistant',
        content: 'Query executed successfully',
        result,
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage: Message = {
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleExampleClick = (exampleQuery: string) => {
    setQuery(exampleQuery)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            LLM Data Analyst
          </h1>
          <p className="text-gray-600">
            Ask questions about NYC Taxi data in natural language
          </p>
        </div>

        {/* Main Content */}
        <div className="bg-white rounded-lg shadow-xl overflow-hidden">
          {/* Messages Area */}
          <div className="h-[600px] overflow-y-auto p-6 space-y-6">
            {messages.length === 0 ? (
              <div className="text-center py-20">
                <h2 className="text-2xl font-semibold text-gray-700 mb-4">
                  Welcome to LLM Data Analyst
                </h2>
                <p className="text-gray-500 mb-8">
                  Try asking a question about the NYC Taxi dataset
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-3xl mx-auto">
                  {exampleQueries.map((example, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleExampleClick(example)}
                      className="p-4 bg-blue-50 hover:bg-blue-100 rounded-lg text-left text-sm text-gray-700 transition-colors"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((message, idx) => (
                <div
                  key={idx}
                  className={`flex ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  <div
                    className={`max-w-4xl w-full ${
                      message.role === 'user'
                        ? 'bg-blue-500 text-white rounded-lg p-4'
                        : 'space-y-4'
                    }`}
                  >
                    {message.role === 'user' ? (
                      <p>{message.content}</p>
                    ) : (
                      <>
                        {message.result ? (
                          <div className="space-y-4">
                            {/* SQL Query */}
                            <div className="bg-gray-100 rounded-lg p-4">
                              <h3 className="text-sm font-semibold text-gray-700 mb-2">
                                Generated SQL:
                              </h3>
                              <pre className="text-xs bg-gray-800 text-green-400 p-3 rounded overflow-x-auto">
                                {message.result.sql}
                              </pre>
                            </div>

                            {/* Chart */}
                            {message.result.chart && (
                              <div className="bg-white border rounded-lg p-4">
                                <Plot
                                  data={JSON.parse(message.result.chart).data}
                                  layout={{
                                    ...JSON.parse(message.result.chart).layout,
                                    autosize: true,
                                  }}
                                  config={{ responsive: true }}
                                  className="w-full"
                                />
                              </div>
                            )}

                            {/* Data Table */}
                            <div className="bg-white border rounded-lg p-4">
                              <div className="flex justify-between items-center mb-3">
                                <h3 className="text-sm font-semibold text-gray-700">
                                  Results ({message.result.row_count} rows)
                                </h3>
                              </div>
                              <div className="overflow-x-auto">
                                <table className="min-w-full text-sm">
                                  <thead>
                                    <tr className="border-b bg-gray-50">
                                      {message.result.columns.map((col) => (
                                        <th
                                          key={col}
                                          className="px-4 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider"
                                        >
                                          {col}
                                        </th>
                                      ))}
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-gray-200">
                                    {message.result.data
                                      .slice(0, 10)
                                      .map((row, rowIdx) => (
                                        <tr key={rowIdx} className="hover:bg-gray-50">
                                          {message.result!.columns.map((col) => (
                                            <td
                                              key={col}
                                              className="px-4 py-2 whitespace-nowrap text-gray-700"
                                            >
                                              {typeof row[col] === 'number'
                                                ? row[col].toLocaleString(
                                                    undefined,
                                                    {
                                                      maximumFractionDigits: 2,
                                                    }
                                                  )
                                                : row[col]}
                                            </td>
                                          ))}
                                        </tr>
                                      ))}
                                  </tbody>
                                </table>
                                {message.result.row_count > 10 && (
                                  <p className="text-xs text-gray-500 mt-2">
                                    Showing first 10 of {message.result.row_count}{' '}
                                    rows
                                  </p>
                                )}
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div className="bg-red-100 border border-red-300 text-red-700 px-4 py-3 rounded">
                            {message.content}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              ))
            )}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-lg p-4">
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                    <span className="text-gray-600 text-sm">
                      Processing query...
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input Area */}
          <div className="border-t bg-gray-50 p-4">
            <form onSubmit={handleSubmit} className="flex space-x-3">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask a question about NYC Taxi data..."
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
              >
                {loading ? 'Processing...' : 'Send'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
