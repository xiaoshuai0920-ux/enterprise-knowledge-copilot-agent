import { useEffect, useState } from 'react'
import { Button, Card, Form, Input, Modal, Select, Table, Tag } from 'antd'
import { api } from '../api/client'

export default function BadCasesPage(){
 const [rows,setRows]=useState<any[]>([]); const [open,setOpen]=useState(false); const [form]=Form.useForm()
 const load=()=>{ api.get('/api/v1/bad-cases').then(r=>setRows(r.data)) }; useEffect(()=>{ load() },[])
 const submit=async()=>{const v=await form.validateFields();await api.post('/api/v1/bad-cases',v);setOpen(false);form.resetFields();load()}
 const cols=[{title:'ID',dataIndex:'id'},{title:'问题',dataIndex:'question'},{title:'错误类型',dataIndex:'error_type',render:(v:string)=><Tag color="orange">{v}</Tag>},{title:'Root Cause',dataIndex:'root_cause'},{title:'Trace',dataIndex:'trace_id'}]
 return <div className="page"><div className="hero"><h1>Bad Case Center</h1><div>线上错误 → Trace 定位 → Root Cause → Golden Dataset → Regression。</div></div><Card title="Bad Cases" extra={<Button type="primary" onClick={()=>setOpen(true)}>新增 Bad Case</Button>}><Table rowKey="id" dataSource={rows} columns={cols}/></Card><Modal title="记录 Bad Case" open={open} onCancel={()=>setOpen(false)} onOk={submit}><Form form={form} layout="vertical"><Form.Item name="question" label="问题" rules={[{required:true}]}><Input.TextArea/></Form.Item><Form.Item name="trace_id" label="Trace ID"><Input/></Form.Item><Form.Item name="error_type" label="错误类型" rules={[{required:true}]}><Select options={['rewrite_error','retrieval_error','rerank_error','acl_error','generation_error','stale_knowledge'].map(x=>({label:x,value:x}))}/></Form.Item><Form.Item name="root_cause" label="Root Cause"><Input.TextArea/></Form.Item><Form.Item name="expected_result" label="期望结果"><Input.TextArea/></Form.Item></Form></Modal></div>
}
