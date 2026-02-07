import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// 系统状态
export const getStatus = () => api.get('/status')
export const getStats = () => api.get('/stats')

// 技能树
export const getGeneralTree = () => api.get('/trees/general')
export const getDomainTree = () => api.get('/trees/domain')
export const getTreeStats = () => api.get('/trees/stats')
export const getSkillRegistry = () => api.get('/trees/registry')
export const setSkillPriority = (type, id, priority) =>
  api.put(`/trees/${type}/skills/${id}/priority`, { priority })
export const unlockSkill = (type, id) =>
  api.put(`/trees/${type}/skills/${id}/unlock`)
export const addSkill = (type, skill) =>
  api.post(`/trees/${type}/skills`, skill)

// 目标
export const getGoals = () => api.get('/goals')
export const createGoal = (data) => api.post('/goals', data)
export const updateGoalStatus = (id, status) =>
  api.put(`/goals/${id}/status`, { status })
export const deleteGoal = (id) => api.delete(`/goals/${id}`)

// 配置
export const getConfig = () => api.get('/config')
export const updateConfig = (updates) => api.put('/config', { updates })

// 进化控制
export const triggerEvolution = () => api.post('/evolve/trigger')
export const startEvolution = () => api.post('/evolve/start')
export const stopEvolution = () => api.post('/evolve/stop')
export const getEvolutionRunning = () => api.get('/evolve/running')

// 日志
export const getLogs = (limit = 100, offset = 0) =>
  api.get('/logs', { params: { limit, offset } })

// 知识库
export const getKnowledge = (params) => api.get('/knowledge', { params })
export const getKnowledgeDetail = (id) => api.get(`/knowledge/${id}`)

export default api
