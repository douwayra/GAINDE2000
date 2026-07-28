export const formatCFA = (value) => {
  if (value === null || value === undefined) return 'N/A';
  if (typeof value === 'string') return value;
  if (value >= 1e12) {
    return (value / 1e12).toFixed(2) + " Trillion CFA";
  } else if (value >= 1e9) {
    return (value / 1e9).toFixed(2) + " Milliard CFA";
  }
  return value.toLocaleString('fr-FR') + " CFA";
};

export const formatWeight = (kg) => {
  if (kg === null || kg === undefined) return 'N/A';
  if (typeof kg === 'string') return kg;
  if (kg >= 1e9) {
    return (kg / 1e9).toFixed(2).replace('.', ',') + " Mds kg";
  } else if (kg >= 1e6) {
    return (kg / 1e6).toFixed(2).replace('.', ',') + " M kg";
  }
  return kg.toLocaleString('fr-FR') + " kg";
};

export const getAuthHeaders = () => {
  const token = localStorage.getItem('orbus_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

export const performLogout = () => {
  localStorage.removeItem('orbus_token');
  localStorage.removeItem('orbus_role');
  localStorage.removeItem('orbus_username');
  localStorage.removeItem('orbus_bureau');
  window.location.reload();
};

export const fetchWithAuth = async (url, options = {}) => {
  const headers = {
    ...getAuthHeaders(),
    ...options.headers,
  };
  
  const response = await fetch(url, {
    ...options,
    headers,
  });
  
  if (response.status === 401) {
    performLogout();
    throw new Error('Non autorisé, redirection vers la page de connexion.');
  }
  
  return response;
};
