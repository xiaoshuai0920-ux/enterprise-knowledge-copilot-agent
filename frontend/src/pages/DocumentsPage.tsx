import { useEffect, useState } from 'react'
import { Card, Table, Tag } from 'antd'
import { api } from '../api/client'

export default function DocumentsPage(){
  const [rows,setRows]=useState<any[]>([])
  useEffect(()=>{api.get('/api/v1/documents').then(r=>setRows(r.data))},[])
  const columns=[
    {title:'文档',dataIndex:'title'}, {title:'版本',dataIndex:'version',render:(v:string)=><Tag>{v||'-'}</Tag>},
    {title:'状态',dataIndex:'status',render:(v:string)=><Tag color={v==='active'?'green':'default'}>{v}</Tag>},
    {title:'来源',dataIndex:'source_type'}, {title:'分类',dataIndex:'category'}, {title:'ACL',dataIndex:'acl_groups',render:(v:string[])=>v.map(x=><Tag key={x} color="blue">{x}</Tag>)},
    {title:'Chunks',dataIndex:'chunk_count'}, {title:'生效时间',dataIndex:'effective_from'}
  ]
  return <div className="page"><div className="hero"><h1>Document Center</h1><div>当前身份只能看到有权访问的文档元数据；旧版本保留用于治理，但不参与当前检索。</div></div><Card><Table rowKey="id" dataSource={rows} columns={columns} pagination={false}/></Card></div>
}
