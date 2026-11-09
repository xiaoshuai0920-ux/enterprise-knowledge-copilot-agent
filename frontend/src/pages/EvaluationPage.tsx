import { useState } from 'react'
import { Button, Card, Progress, Table, Tag } from 'antd'
import { api } from '../api/client'

export default function EvaluationPage(){
 const [data,setData]=useState<any>(null); const [loading,setLoading]=useState(false)
 const run=async()=>{setLoading(true);try{setData((await api.post('/api/v1/eval/run')).data)}finally{setLoading(false)}}
 const cols=[{title:'Case',dataIndex:'case_id'},{title:'结果',dataIndex:'passed',render:(v:boolean)=><Tag color={v?'green':'red'}>{v?'PASS':'FAIL'}</Tag>},{title:'Route',dataIndex:'route'},{title:'问题',dataIndex:'question'},{title:'回答',dataIndex:'answer'}]
 return <div className="page"><div className="hero"><h1>Evaluation</h1><div>版本、精确错误码、ACL 拒绝/允许、Multi-hop 五类 Golden Case。</div></div><Card><Button type="primary" loading={loading} onClick={run}>运行 Golden Dataset</Button>{data&&<><Progress percent={Math.round(data.passed/data.total*100)} status={data.passed===data.total?'success':'exception'} style={{marginTop:20}}/><Table rowKey="case_id" dataSource={data.results} columns={cols} pagination={false}/></>}</Card></div>
}
