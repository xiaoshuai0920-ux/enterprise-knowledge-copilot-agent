import { useState } from 'react'
import { Alert, Button, Card, Collapse, Input, List, Space, Tag, Timeline, Typography, message } from 'antd'
import { SendOutlined } from '@ant-design/icons'
import { api } from '../api/client'
import type { ChatResponse } from '../types'

const examples=[
  'P6 去上海出差住宿标准是多少？',
  'ERR_PAYMENT_5008 是什么意思？',
  '退款接口超时以后可以直接重试吗？',
  'Phoenix 项目技术负责人的上级的上级是谁？',
  '公司高管奖金是怎么计算的？'
]

type Msg={role:'user'|'assistant';content:string}

export default function ChatPage(){
  const [question,setQuestion]=useState('P6 去上海出差住宿标准是多少？')
  const [history,setHistory]=useState<Msg[]>([])
  const [result,setResult]=useState<ChatResponse|null>(null)
  const [loading,setLoading]=useState(false)
  const ask=async()=>{
    if(!question.trim()) return
    setLoading(true)
    try{
      const payload={question,history:history.slice(-6)}
      const {data}=await api.post<ChatResponse>('/api/v1/chat',payload)
      setResult(data)
      setHistory(h=>[...h,{role:'user',content:question},{role:'assistant',content:data.answer}])
    }catch(e:any){message.error(e?.response?.data?.detail||'请求失败')}finally{setLoading(false)}
  }
  return <div className="page">
    <div className="hero"><h1>Knowledge Chat</h1><div>不是“PDF + Vector TopK”，而是完整的企业知识检索链路。</div></div>
    <Card style={{marginBottom:16}}>
      <Space wrap style={{marginBottom:12}}>{examples.map(x=><Button size="small" key={x} onClick={()=>setQuestion(x)}>{x}</Button>)}</Space>
      <Input.TextArea value={question} onChange={e=>setQuestion(e.target.value)} autoSize={{minRows:3,maxRows:5}} placeholder="输入企业知识问题..."/>
      <Button type="primary" icon={<SendOutlined/>} loading={loading} onClick={ask} style={{marginTop:12}}>发送</Button>
    </Card>
    {result && <div className="chat-shell">
      <div>
        <Card title={<Space><span>回答</span><Tag color="blue">{result.route}</Tag><Tag>{Math.round(result.confidence*100)}%</Tag></Space>}>
          {result.insufficient_evidence && <Alert type="warning" showIcon message="证据不足或权限不可达" style={{marginBottom:12}}/>}
          {result.rewritten_query && <div style={{marginBottom:12}}><Typography.Text type="secondary">Rewrite：</Typography.Text><span className="code">{result.rewritten_query}</span></div>}
          <div className="answer">{result.answer}</div>
          <div style={{marginTop:16}}><Typography.Text type="secondary">trace_id：</Typography.Text><span className="code">{result.trace_id}</span></div>
        </Card>
        <Card title="Citation / Evidence" style={{marginTop:16}}>
          <List dataSource={result.citations} locale={{emptyText:'没有可访问证据'}} renderItem={(c,i)=><List.Item><Card size="small" className="citation-card" style={{width:'100%'}} title={`[${i+1}] ${c.title}`} extra={<Space><Tag>{c.version||'-'}</Tag><Tag color="green">score {c.score.toFixed(3)}</Tag></Space>}><div><b>{c.section}</b></div><div style={{marginTop:8,lineHeight:1.7}}>{c.content}</div></Card></List.Item>}/>
        </Card>
      </div>
      <Card title="RAG Trace">
        <Timeline items={result.trace.map(t=>({color:t.status==='success'?'green':'red',children:<div><div className="timeline-title">{t.node} <Tag>{t.latency_ms}ms</Tag></div><Collapse ghost size="small" items={[{key:'1',label:'查看输入/输出',children:<div className="trace-json">{JSON.stringify({input:t.input,output:t.output},null,2)}</div>}]} /></div>}))}/>
      </Card>
    </div>}
  </div>
}
