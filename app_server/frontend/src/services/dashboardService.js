import api from './api';

export const dashboardService = {
  getOverview: async () => {
    const response = await api.get('/api/dashboard');
    return response.data;
  },
};
