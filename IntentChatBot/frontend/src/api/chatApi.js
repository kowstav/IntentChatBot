import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const chatApi = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const sendMessage = async (message) => {
  try {
    const response = await chatApi.post('/api/v1/chat', {
      text: message,
    });
    return response.data;
  } catch (error) {
    console.error('Error sending message:', error);
    throw error;
  }
};

export const initializeWebSocket = () => {
  const ws = new WebSocket(`ws://${window.location.hostname}/ws`);
  
  ws.onopen = () => {
    console.log('WebSocket Connected');
  };
  
  return ws;
};