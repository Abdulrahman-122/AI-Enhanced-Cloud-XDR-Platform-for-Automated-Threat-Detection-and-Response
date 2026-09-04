import api from './api';

export const alertService = {
  getAlerts: async (params = {}) => {
    const response = await api.get('/api/alerts', { params });
    return response.data;
  },

  getAlertById: async (alertId) => {
    const response = await api.get(`/api/alerts/${alertId}`);
    return response.data;
  },
};
