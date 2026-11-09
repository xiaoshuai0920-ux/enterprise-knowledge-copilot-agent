import { useState } from 'react'
import { Button, Card, Input, Timeline, message } from 'antd'
import { api } from '../api/client'

export default function TracePage(){
  const [id,setId]=useState(''); const [trace,setTrace]=useState<any[]>([])
  const load=async()=>{try{const r=await api.get(`/api/v1/traces/${id}`);setTrace(r.data)}catch{message.error('Trace 不存在')}}
  return <div className="page"><div className="hero"><h1>RAG Trace Explorer</h1><div>回答错了，不要一句“模型幻觉”带过。逐层看 Rewrite、ACL、Recall、Rerank、Context、Generation。</div></div><Card><Input.Search value={id} onChange={e=>setId(e.target.value)} onSearch={load} enterButton="查询 Trace" placeholder="输入 Knowledge Chat 返回的 trace_id"/></Card><Card title="执行链路" style={{marginTop:16}}><Timeline items={trace.map(t=>({color:t.status==='success'?'green':'red',children:<div><b>{t.node}</b> · {t.latency_ms}ms<pre className="trace-json">{JSON.stringify({input:t.input,output:t.output},null,2)}</pre></div>}))}/></Card></div>
}
