// IntentChatBot/frontend/src/api/chatApi.js
import axios from 'axios';

// The API_URL is for HTTP requests to your backend
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// The WebSocket URL needs to point to your backend's WebSocket endpoint
// If your backend is at http://localhost:8000, the WebSocket is usually ws://localhost:8000/ws
const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';

export const chatApi = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const sendMessage = async (message) => {
  try {
    // This function seems to be for an HTTP endpoint, ensure this is intended
    // if most communication is over WebSocket.
    const response = await chatApi.post('/api/v1/chat', { // Ensure this matches your HTTP endpoint in chatbot.py
      text: message,
      // You might need to include user_id or session_id here if your HTTP endpoint expects it
    });
    return response.data;
  } catch (error) {
    console.error('Error sending message via HTTP:', error);
    throw error;
  }
};

export const initializeWebSocket = () => {
  // Use the defined WS_URL
  const ws = new WebSocket(WS_URL);
  
  ws.onopen = () => {
    console.log('WebSocket Connected to:', WS_URL);
  };
  
  ws.onclose = (event) => {
    console.log('WebSocket Disconnected:', event.reason, event.code);
  };

  ws.onerror = (error) => {
    console.error('WebSocket Error:', error);
  };
  
  return ws;
};

// Optional: If you need to send feedback via HTTP POST
export const sendFeedback = async (feedbackData) => {
  try {
    // Ensure your backend has a /api/v1/feedback endpoint or adjust as needed
    const response = await chatApi.post('/api/v1/feedback', feedbackData);
    return response.data;
  } catch (error) {
    console.error('Error sending feedback:', error);
    throw error;
  }
};