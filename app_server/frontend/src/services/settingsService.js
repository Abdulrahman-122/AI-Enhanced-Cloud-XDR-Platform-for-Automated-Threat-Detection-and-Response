import api from './api';

export const settingsService = {
  getDiagnostics: async () => {
    const response = await api.get('/api/settings/diagnostics');
    return response.data;
  },

  updateProfile: async (profileData) => {
    const response = await api.put('/api/settings/profile', profileData);
    if (response.data) {
      localStorage.setItem('xdr_user_info', JSON.stringify(response.data));
    }
    return response.data;
  },
};
