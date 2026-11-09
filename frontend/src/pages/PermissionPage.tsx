import { Card, Col, Row, Space, Tag, Typography } from 'antd'
import { identities, useIdentityStore } from '../store/identity'

export default function PermissionPage(){
 const {identity,setIdentity}=useIdentityStore()
 return <div className="page"><div className="hero"><h1>Permission Center</h1><div>演示 ACL 必须发生在 Retrieval 之前。切换身份后再问“公司高管奖金是怎么计算的？”。</div></div><Row gutter={[16,16]}>{identities.map(x=><Col xs={24} md={12} lg={6} key={x.name}><Card hoverable onClick={()=>setIdentity(x)} style={{borderColor:identity.name===x.name?'#1677ff':undefined}}><Space direction="vertical"><Typography.Title level={4}>{x.name}</Typography.Title><div>role: <span className="code">{x.role}</span></div><div>{x.groups.map(g=><Tag color="blue" key={g}>{g}</Tag>)}</div>{identity.name===x.name&&<Tag color="green">当前身份</Tag>}</Space></Card></Col>)}</Row><Card style={{marginTop:16}} title="为什么不是“先召回再让模型判断权限”？"><p>因为敏感 Chunk 一旦进入 LLM Context，数据已经越过了权限边界。正确链路是：<b>Security Context → ACL Filter → Retrieval → LLM</b>。</p></Card></div>
}
