// frontend/src/components/ChatWindow.jsx
import React, { useState, useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble'; // Using your MessageBubble component
import { sendMessage, initializeWebSocket } from '../api/chatApi'; // Using your chatApi.js
import styled from 'styled-components'; // For styling ChatWindow itself if needed

// Basic styling for ChatWindow elements using styled-components for consistency
// You can expand these or use a global CSS / Tailwind approach as preferred.
const ChatWrapper = styled.div`
  display: flex;
  flex-direction: column;
  height: calc(100vh - 40px); // Example height, adjust as needed
  max-width: 600px;
  margin: 20px auto;
  border: 1px solid #ccc;
  border-radius: 8px;
  overflow: hidden;
  font-family: Arial, sans-serif;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
`;

const Header = styled.header`
  background-color: #f1f1f1;
  padding: 10px;
  text-align: center;
  border-bottom: 1px solid #ccc;
  font-size: 1.2em;
  font-weight: bold;
`;

const MessageArea = styled.div`
  flex-grow: 1;
  overflow-y: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
  background-color: #fff; // Set a background color for message area
`;

const InputArea = styled.div`
  display: flex;
  padding: 10px;
  border-top: 1px solid #ccc;
  background-color: #f9f9f9;
`;

const TextInput = styled.input`
  flex-grow: 1;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 20px;
  margin-right: 10px;
  font-size: 1em;
  &:focus {
    outline: none;
    border-color: #007bff;
  }
`;

const SendButton = styled.button`
  padding: 10px 20px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  font-size: 1em;
  &:hover {
    background-color: #0056b3;
  }
  &:disabled {
    background-color: #cccccc;
    cursor: not-allowed;
  }
`;

const TypingIndicator = styled.div`
  padding: 5px 10px;
  font-style: italic;
  color: #777;
  text-align: left;
`;

const ErrorDisplay = styled.p`
  color: red;
  text-align: center;
  padding: 5px;
  font-size: 0.9em;
`;

// Feedback styling (basic)
const FeedbackSection = styled.div`
  padding: 10px;
  border-top: 1px solid #eee;
  background-color: #f9f9f9;
  font-size: 0.9em;

  & > p {
    margin-bottom: 5px;
  }

  textarea {
    width: calc(100% - 20px);
    padding: 8px;
    margin-top: 5px;
    margin-bottom: 5px;
    border: 1px solid #ddd;
    border-radius: 4px;
    min-height: 40px;
  }
`;

const StarButton = styled.button`
  background: none;
  border: none;
  color: ${props => (props.selected ? 'gold' : '#ccc')};
  font-size: 1.5em;
  cursor: pointer;
  margin: 0 2px;
  padding: 0;
  &:hover {
    color: ${props => (props.selected ? 'darkorange' : 'lightgrey')};
  }
`;


const generateId = () => `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

const ChatWindow = () => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [sessionId, setSessionId] = useState(null); // For HTTP session management if used
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const [websocket, setWebsocket] = useState(null);

  // Feedback state
  const [showFeedback, setShowFeedback] = useState(false);
  const [currentRating, setCurrentRating] = useState(0);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [lastBotMessageForFeedback, setLastBotMessageForFeedback] = useState(null);


  useEffect(() => {
    // Initialize WebSocket connection
    const ws = initializeWebSocket(); // From your chatApi.js
    setWebsocket(ws);

    ws.onmessage = (event) => {
      setIsLoading(false);
      const data = JSON.parse(event.data);
      
      if (data.error) {
        console.error("WebSocket Error:", data.error);
        setError(data.error);
        const errorBotMessage = {
            id: generateId(),
            text: `Error: ${data.error}. Please try again.`,
            sender: 'bot',
            isError: true, // You might want to style this in MessageBubble
            timestamp: new Date().toISOString(),
        };
        setMessages((prevMessages) => [...prevMessages, errorBotMessage]);
        return;
      }

      const botResponse = {
        id: generateId(),
        text: data.response,
        sender: 'bot',
        timestamp: new Date().toISOString(), // Assuming backend doesn't send timestamp for WS message
        intent: data.intent,
        isEscalated: data.requires_human_escalation, // Map from backend field
        escalationTicketId: data.escalation_ticket_id
      };
      setMessages((prevMessages) => [...prevMessages, botResponse]);

      if (data.intent !== 'goodbye' && !data.requires_human_escalation) {
        setLastBotMessageForFeedback(botResponse);
        setShowFeedback(true);
        setCurrentRating(0);
        setFeedbackComment('');
      } else {
        setShowFeedback(false);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket Disconnected');
      // Optionally, you can try to reconnect here or notify the user
    };

    ws.onerror = (errorEvent) => {
      console.error('WebSocket Error:', errorEvent);
      setError('WebSocket connection error. Please refresh.');
      setIsLoading(false);
    };
    
    // Initial welcome message
    setMessages([
      {
        id: generateId(),
        text: "Hello! How can I assist you today?",
        sender: 'bot',
        timestamp: new Date().toISOString(),
      },
    ]);

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async () => {
    if (inputValue.trim() === '' || !websocket || websocket.readyState !== WebSocket.OPEN) {
      if (!websocket || websocket.readyState !== WebSocket.OPEN) {
        setError("WebSocket is not connected. Please wait or refresh.");
      }
      return;
    }

    const userMessage = {
      id: generateId(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date().toISOString(),
    };

    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setIsLoading(true);
    setError(null);
    setShowFeedback(false); // Hide feedback form when new user message is sent

    // Send message via WebSocket
    websocket.send(JSON.stringify({ text: inputValue, session_id: sessionId /* if you manage it */ }));
    setInputValue('');
  };


  const handleInputChange = (e) => {
    setInputValue(e.target.value);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !isLoading) {
      handleSendMessage();
    }
  };

  // HTTP API URL (from your chatApi.js, primarily for feedback if not sent over WS)
  const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  const handleFeedbackSubmit = async () => {
    // This assumes feedback is sent over HTTP POST as per original design
    // If feedback is to be sent over WebSocket, adjust accordingly.
    if (!lastBotMessageForFeedback || currentRating === 0) {
      alert("Please select a rating.");
      return;
    }
    setIsLoading(true);
    try {
      // Assuming your backend /api/v1/chat or a new /api/v1/feedback endpoint
      // This matches the /feedback endpoint from the Python backend we discussed
      const response = await fetch(`${API_BASE_URL}/api/v1/feedback`, { // Adjust if your feedback endpoint is different
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId || "ws_session", // Use appropriate session/conversation ID
          // chat_log_id: backend might generate this, or link to conversation
          rating: currentRating,
          comment: feedbackComment,
        }),
      });
      if (!response.ok) throw new Error(`Feedback submission failed: ${response.statusText}`);
      
      const feedbackConfirmationMessage = {
        id: generateId(),
        text: "Thanks for your feedback!",
        sender: 'bot',
        timestamp: new Date().toISOString(),
      };
      setMessages((prevMessages) => [...prevMessages, feedbackConfirmationMessage]);

    } catch (err) {
      console.error("Feedback error:", err);
      setError(`Feedback error: ${err.message}`);
    } finally {
      setIsLoading(false);
      setShowFeedback(false);
      setCurrentRating(0);
      setFeedbackComment('');
    }
  };


  return (
    <ChatWrapper>
      <Header>ChatBot Support</Header>
      <MessageArea>
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {isLoading && <TypingIndicator>Bot is typing...</TypingIndicator>}
        <div ref={messagesEndRef} />
      </MessageArea>
      {error && <ErrorDisplay>{error}</ErrorDisplay>}
      
      {showFeedback && lastBotMessageForFeedback && (
          <FeedbackSection>
            <p>How helpful was that last response?</p>
            <div>
              {[1, 2, 3, 4, 5].map((star) => (
                <StarButton
                  key={star}
                  selected={currentRating >= star}
                  onClick={() => setCurrentRating(star)}
                  aria-label={`Rate ${star} star`}
                >
                  ★
                </StarButton>
              ))}
            </div>
            {currentRating > 0 && (
                 <textarea
                    value={feedbackComment}
                    onChange={(e) => setFeedbackComment(e.target.value)}
                    placeholder="Optional: Add a comment..."
                    rows="2"
                />
            )}
            <SendButton // Reusing SendButton style
              onClick={handleFeedbackSubmit}
              disabled={isLoading || currentRating === 0}
            >
              Submit Feedback
            </SendButton>
          </FeedbackSection>
        )}

      <InputArea>
        <TextInput
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
          disabled={isLoading || (websocket && websocket.readyState !== WebSocket.OPEN)}
        />
        <SendButton 
            onClick={handleSendMessage} 
            disabled={isLoading || inputValue.trim() === '' || (websocket && websocket.readyState !== WebSocket.OPEN)}
        >
          Send
        </SendButton>
      </InputArea>
    </ChatWrapper>
  );
};

export default ChatWindow;