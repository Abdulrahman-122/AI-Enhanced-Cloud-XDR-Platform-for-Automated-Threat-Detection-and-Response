import api from './api';

export const agentService = {
  getAgents: async (params = {}) => {
    const response = await api.get('/api/agents', { params });
    return response.data;
  },

  getAgentById: async (agentId) => {
    const response = await api.get(`/api/agents/${agentId}`);
    return response.data;
  },
};
