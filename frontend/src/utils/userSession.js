import { apiFetch } from '../config';

export const fetchAndStoreUserName = async () => {
  const token = sessionStorage.getItem('token');

  if (!token) {
    return null;
  }

  const response = await apiFetch('/me', {
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
