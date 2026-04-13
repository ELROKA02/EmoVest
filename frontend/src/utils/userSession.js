const API_BASE_URL = 'http://localhost:8000';

export const fetchAndStoreUserName = async () => {
  const token = localStorage.getItem('token');

  if (!token) {
    return null;
  }

  const response = await fetch(`${API_BASE_URL}/me`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error('No se pudo obtener el usuario actual');
  }

  const data = await response.json();
  const name = data?.name?.trim();

  if (name) {
    localStorage.setItem('userName', name);
  }

  return name || null;
};