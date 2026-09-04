import api from './api';

export const authService = {
  login: async (usernameOrEmail, password) => {
    const formData = new URLSearchParams();

    formData.append('username', usernameOrEmail);
    formData.append('password', password);

    const response = await api.post('/api/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    if (response.data.access_token) {
      localStorage.setItem('xdr_auth_token', response.data.access_token);
      localStorage.setItem(
        'xdr_user_info',
        JSON.stringify(response.data.user)
      );
    }

    return response.data;
  },

  register: async (userData) => {
    const response = await api.post('/api/auth/register', userData);
    return response.data;
  },

  getCurrentUser: async () => {
    const response = await api.get('/api/home/me');

    if (response.data.user) {
      localStorage.setItem(
        'xdr_user_info',
        JSON.stringify(response.data.user)
      );
    }

    return response.data;
  },

  getStoredUser: () => {
    const userJson = localStorage.getItem('xdr_user_info');

    if (userJson) {
      try {
        return JSON.parse(userJson);
      } catch (e) {
        return null;
      }
    }

    return null;
  },

  getToken: () => {
    return localStorage.getItem('xdr_auth_token');
  },

  isAuthenticated: () => {
    return !!localStorage.getItem('xdr_auth_token');
  },

  logout: () => {
    localStorage.removeItem('xdr_auth_token');
    localStorage.removeItem('xdr_user_info');
    window.location.href = '/login';
  },
};
