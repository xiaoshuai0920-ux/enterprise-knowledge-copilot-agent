export type Identity = {
  name: string
  userId: string
  role: string
  department: string
  groups: string[]
}

export type Citation = {
  chunk_id: string
  document_id: string
  title: string
  section?: string
  version?: string
  source_uri?: string
  content: string
  score: number
}

export type TraceStep = {
  node: string
  status: string
  latency_ms: number
  input?: unknown
  output?: unknown
}

export type ChatResponse = {
  trace_id: string
  route: string
  answer: string
  rewritten_query?: string
  keywords: string[]
  citations: Citation[]
  trace: TraceStep[]
  confidence: number
  insufficient_evidence: boolean
}
