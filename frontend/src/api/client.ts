import axios from 'axios'
import { useIdentityStore } from '../store/identity'

export const api = axios.create({ baseURL: '/' })

api.interceptors.request.use((config) => {
  const identity = useIdentityStore.getState().identity
  config.headers['x-user-id'] = identity.userId
  config.headers['x-tenant-id'] = 'tenant_demo'
  config.headers['x-user-role'] = identity.role
  config.headers['x-user-department'] = identity.department
  config.headers['x-user-groups'] = identity.groups.join(',')
  return config
})
