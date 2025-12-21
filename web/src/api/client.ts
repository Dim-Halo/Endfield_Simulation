import axios from 'axios';

// Assume backend is running on port 8000
const API_URL = 'http://127.0.0.1:8000';

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});
