import { create } from 'zustand'
import type { Identity } from '../types'

export const identities: Identity[] = [
  { name: '普通研发', userId: 'u_dev_001', role: 'developer', department: 'engineering', groups: ['all', 'engineering'] },
  { name: 'HR 管理员', userId: 'u_hr_001', role: 'hr-admin', department: 'hr', groups: ['all', 'hr-admin'] },
  { name: '公司高管', userId: 'u_exec_001', role: 'executive', department: 'executive', groups: ['all', 'executive'] },
  { name: 'SRE', userId: 'u_sre_001', role: 'sre', department: 'engineering', groups: ['all', 'engineering', 'sre'] }
]

type State = { identity: Identity; setIdentity: (identity: Identity) => void }

export const useIdentityStore = create<State>((set) => ({
  identity: identities[0],
  setIdentity: (identity) => set({ identity })
}))
