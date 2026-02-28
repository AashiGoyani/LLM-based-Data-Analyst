'use client'

import { useState } from 'react'
import dynamic from 'next/dynamic'

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

const exampleQueries = [
  { icon: '💳', text: 'Show total trips by payment type' },
  { icon: '📈', text: 'What is the monthly revenue trend for 2016?' },
  { icon: '🏆', text: 'Show the top 10 days with highest total revenue' },
  { icon: '🕐', text: 'Show hourly trip count on January 1 2016' },
]

export default function Home() {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim() || loading) return

    const userMessage: Message = { role: 'user', content: query.trim() }
    setMessages((prev) => [...prev, userMessage])
    setQuery('')
    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userMessage.content, generate_chart: true }),
      })

      if (!response.ok) throw new Error(`API error: ${response.statusText}`)

      const result: QueryResult = await response.json()
      setMessages((prev) => [...prev, { role: 'assistant', content: 'ok', result }])
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}` },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-gray-900 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center gap-3 shadow-sm">
        <span className="text-2xl"></span>
        <div>
          <h1 className="text-lg font-bold text-gray-800 leading-none">NYC Taxi Analyst</h1>
          <p className="text-xs text-gray-400">Powered by Groq + LLaMA</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
          <span className="text-xs text-gray-400">800K rows loaded</span>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6 max-w-5xl w-full mx-auto">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full min-h-[60vh] text-center">
            <span className="text-6xl mb-4"></span>
            <h2 className="text-3xl font-bold text-gray-800 mb-2">NYC Taxi Data Analyst</h2>
            <p className="text-gray-400 mb-10 text-sm">Ask anything about 800K taxi trips in natural language</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl">
              {exampleQueries.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => setQuery(q.text)}
                  className="flex items-center gap-3 p-4 bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-400 rounded-xl text-left text-sm text-gray-600 hover:text-blue-700 transition-all shadow-sm"
                >
                  <span className="text-xl">{q.icon}</span>
                  <span>{q.text}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message, idx) => (
            <div key={idx} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {message.role === 'user' ? (
                <div className="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 max-w-xl text-sm shadow">
                  {message.content}
                </div>
              ) : (
                <div className="w-full space-y-4">
                  {message.result ? (
                    <>
                      {/* SQL */}
                      <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
                        <p className="text-xs text-gray-400 uppercase tracking-wider mb-2 font-semibold">Generated SQL</p>
                        <pre className="text-xs text-green-400 overflow-x-auto whitespace-pre-wrap">{message.result.sql}</pre>
                      </div>

                      {/* Chart */}
                      {message.result.chart && (
                        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                          <Plot
                            data={JSON.parse(message.result.chart).data}
                            layout={{
                              ...JSON.parse(message.result.chart).layout,
                              autosize: true,
                              paper_bgcolor: 'rgba(0,0,0,0)',
                              plot_bgcolor: 'rgba(0,0,0,0)',
                              font: { color: '#1f2937' },
                              xaxis: { gridcolor: '#e5e7eb', zerolinecolor: '#e5e7eb' },
                              yaxis: { gridcolor: '#e5e7eb', zerolinecolor: '#e5e7eb' },
                            }}
                            config={{ responsive: true, displayModeBar: false }}
                            className="w-full"
                          />
                        </div>
                      )}

                      {/* Table */}
                      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                        <p className="text-xs text-gray-400 uppercase tracking-wider mb-3 font-semibold">
                          Results — {message.result.row_count} rows
                        </p>
                        <div className="overflow-x-auto">
                          <table className="min-w-full text-sm">
                            <thead>
                              <tr className="border-b border-slate-200 bg-slate-50">
                                {message.result.columns.map((col) => (
                                  <th key={col} className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                                    {col}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                              {message.result.data.slice(0, 10).map((row, rowIdx) => (
                                <tr key={rowIdx} className="hover:bg-blue-50 transition-colors">
                                  {message.result!.columns.map((col) => (
                                    <td key={col} className="px-4 py-2 text-gray-700 whitespace-nowrap">
                                      {typeof row[col] === 'number'
                                        ? row[col].toLocaleString(undefined, { maximumFractionDigits: 2 })
                                        : row[col]}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          {message.result.row_count > 10 && (
                            <p className="text-xs text-gray-400 mt-2">Showing 10 of {message.result.row_count} rows</p>
                          )}
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-xl text-sm">
                      {message.content}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-slate-200 rounded-xl px-4 py-3 flex items-center gap-3 shadow-sm">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </div>
              <span className="text-gray-400 text-sm">Generating SQL...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-slate-200 bg-white px-4 py-4 shadow-md">
        <form onSubmit={handleSubmit} className="flex gap-3 max-w-5xl mx-auto">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question about NYC Taxi data..."
            className="flex-1 px-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-200 disabled:text-slate-400 text-white rounded-xl font-medium text-sm transition-colors"
          >
            {loading ? 'Running...' : 'Ask'}
          </button>
        </form>
      </div>
    </div>
  )
}
