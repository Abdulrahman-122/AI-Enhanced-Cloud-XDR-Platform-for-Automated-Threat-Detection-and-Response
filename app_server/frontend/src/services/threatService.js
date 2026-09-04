import api from './api';

export const threatService = {
  getThreatIntelligence: async () => {
    const response = await api.get('/api/threats');
    return response.data;
  },
};
