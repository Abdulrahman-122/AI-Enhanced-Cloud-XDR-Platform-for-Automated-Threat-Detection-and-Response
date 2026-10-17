import api from './api';

export const reportService = {
  getSummary: async () => {
    const response = await api.get('/api/reports/summary');
    return response.data;
  },

  downloadAlertsCsv: async () => {
    const response = await api.get('/api/reports/export/alerts.csv', {
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `xdr_security_alerts_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
};
