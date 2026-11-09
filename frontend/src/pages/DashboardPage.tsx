import { useEffect, useState } from 'react'
import { Card, Col, Row, Space, Statistic, Tag, Typography } from 'antd'
import ReactECharts from 'echarts-for-react'
import { api } from '../api/client'

export default function DashboardPage(){
  const [data,setData]=useState<any>(null)
  useEffect(()=>{ api.get('/api/v1/dashboard').then(r=>setData(r.data)) },[])
  const option={xAxis:{type:'category',data:data?.pipeline||[]},yAxis:{type:'value'},series:[{type:'bar',data:(data?.pipeline||[]).map((_:string,i:number)=>i+1)}],tooltip:{}}
  return <div className="page">
    <div className="hero"><h1>企业知识助手运行总览</h1><div>权限前置、版本治理、Hybrid RAG、Rerank、Citation、Multi-hop、Trace、Evaluation。</div></div>
    <Row gutter={[16,16]}>
      <Col xs={24} sm={12} lg={6}><Card className="metric-card"><Statistic title="知识文档" value={data?.documents||0}/></Card></Col>
      <Col xs={24} sm={12} lg={6}><Card className="metric-card"><Statistic title="Chunks" value={data?.chunks||0}/></Card></Col>
      <Col xs={24} sm={12} lg={6}><Card className="metric-card"><Statistic title="Trace Runs" value={data?.traces||0}/></Card></Col>
      <Col xs={24} sm={12} lg={6}><Card className="metric-card"><Statistic title="Open Bad Cases" value={data?.open_bad_cases||0}/></Card></Col>
    </Row>
    <Row gutter={[16,16]} style={{marginTop:16}}>
      <Col xs={24} lg={16}><Card title="RAG Pipeline"><ReactECharts option={option} style={{height:320}}/></Card></Col>
      <Col xs={24} lg={8}><Card title="知识治理状态">
        <Space direction="vertical" size="large"><div><Typography.Text type="secondary">当前版本</Typography.Text><br/><Tag color="green">active {data?.versions?.active||0}</Tag></div><div><Typography.Text type="secondary">历史版本</Typography.Text><br/><Tag>inactive {data?.versions?.inactive||0}</Tag></div><div><Typography.Text type="secondary">核心链路</Typography.Text><br/>{(data?.pipeline||[]).map((x:string)=><Tag key={x} style={{marginTop:6}}>{x}</Tag>)}</div></Space>
      </Card></Col>
    </Row>
  </div>
}
