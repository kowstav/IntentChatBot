import React, { useState, useEffect, useRef } from 'react';

// Helper function to get a unique ID for messages if needed
const generateId = () => `msg-${Math.random().toString(36).substr(2, 9)}`;

// API base URL - ensure your FastAPI backend is running on this port
const API_BASE_URL = 'http://localhost:8000';

// Main App Component
function App() {
  // State variables
  const [messages, setMessages] = useState([]); // Stores all chat messages
  const [inputValue, setInputValue] = useState(''); // Current value of the input field
  const [sessionId, setSessionId] = useState(null); // Current chat session ID
  const [isLoading, setIsLoading] = useState(false); // True when waiting for bot response
  const [error, setError] = useState(null); // Stores any API error messages
  const [showFeedback, setShowFeedback] = useState(false); // To show feedback form
  const [currentRating, setCurrentRating] = useState(0);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [lastBotMessageForFeedback, setLastBotMessageForFeedback] = useState(null);

  // Ref for scrolling to the bottom of the chat
  const messagesEndRef = useRef(null);

  // Effect to initialize session and add a welcome message
  useEffect(() => {
    // Generate a new session ID when the component mounts if one doesn't exist
    // In a real app, you might fetch this or have it provided.
    // For now, we let the backend generate it on the first message.
    setMessages([
      {
        id: generateId(),
        text: "Hello! I'm your friendly support bot. How can I help you today?",
        sender: 'bot',
        timestamp: new Date(),
      },
    ]);
  }, []);

  // Effect to scroll to the bottom of messages when new messages are added
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Function to handle sending a message
  const handleSendMessage = async () => {
    if (inputValue.trim() === '') return; // Don't send empty messages

    const userMessage = {
      id: generateId(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setInputValue(''); // Clear input field
    setIsLoading(true); // Show loading indicator
    setError(null); // Clear previous errors

    try {
      const requestBody = {
        message: userMessage.text,
        session_id: sessionId, // Will be null for the first message
        // user_id: "some_user_123" // Optional: if you have user authentication
      };

      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Unknown server error" }));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Update session ID if it's the first message response
      if (data.session_id && !sessionId) {
        setSessionId(data.session_id);
      }

      const botResponse = {
        id: generateId(),
        text: data.response_message,
        sender: 'bot',
        timestamp: new Date(),
        intent: data.debug_intent, // For display/debug
        isEscalated: data.escalated,
        escalationTicketId: data.escalation_ticket_id
      };

      setMessages((prevMessages) => [...prevMessages, botResponse]);
      
      // If bot response is not a goodbye message and not an escalation, show feedback option
      if (data.debug_intent !== 'goodbye' && !data.escalated) {
        setLastBotMessageForFeedback(botResponse); // Store the message for feedback context
        setShowFeedback(true);
        setCurrentRating(0); // Reset rating
        setFeedbackComment(''); // Reset comment
      } else {
        setShowFeedback(false);
      }


    } catch (err) {
      console.error("Failed to send message:", err);
      setError(err.message);
      const errorBotMessage = {
        id: generateId(),
        text: `Error: ${err.message}. Please try again.`,
        sender: 'bot',
        isError: true,
        timestamp: new Date(),
      };
      setMessages((prevMessages) => [...prevMessages, errorBotMessage]);
    } finally {
      setIsLoading(false); // Hide loading indicator
    }
  };

  // Function to handle feedback submission
  const handleFeedbackSubmit = async () => {
    if (!sessionId || currentRating === 0) {
      alert("Please select a rating to submit feedback."); // Simple alert for now
      return;
    }

    setIsLoading(true); // Reuse loading state for feedback submission
    try {
      const feedbackRequestBody = {
        session_id: sessionId,
        // chat_log_id: lastBotMessageForFeedback?.id, // This ID is frontend-generated, backend might need its own log ID
        rating: currentRating,
        comment: feedbackComment,
      };

      const response = await fetch(`${API_BASE_URL}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(feedbackRequestBody),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Feedback submission failed" }));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const feedbackResponseData = await response.json();
      console.log("Feedback submitted:", feedbackResponseData);
      
      // Add a small confirmation message to the chat
       const feedbackConfirmationMessage = {
        id: generateId(),
        text: "Thanks for your feedback!",
        sender: 'bot',
        timestamp: new Date(),
      };
      setMessages((prevMessages) => [...prevMessages, feedbackConfirmationMessage]);


    } catch (err) {
      console.error("Failed to submit feedback:", err);
      setError(`Feedback error: ${err.message}`); // Show feedback error
       const feedbackErrorMessage = {
        id: generateId(),
        text: `Sorry, couldn't submit feedback: ${err.message}`,
        sender: 'bot',
        isError: true,
        timestamp: new Date(),
      };
      setMessages((prevMessages) => [...prevMessages, feedbackErrorMessage]);
    } finally {
      setIsLoading(false);
      setShowFeedback(false); // Hide feedback form after submission attempt
      setCurrentRating(0);
      setFeedbackComment('');
    }
  };


  // Handle input change
  const handleInputChange = (e) => {
    setInputValue(e.target.value);
  };

  // Handle Enter key press in input field
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !isLoading) {
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 p-4 font-sans text-white">
      <div className="bg-slate-700 shadow-2xl rounded-lg w-full max-w-lg flex flex-col h-[calc(100vh-4rem)] max-h-[700px]">
        {/* Header */}
        <header className="bg-slate-800 p-4 rounded-t-lg shadow-md">
          <h1 className="text-xl font-semibold text-center text-sky-400">Customer Support Chat</h1>
          {sessionId && <p className="text-xs text-center text-slate-400 mt-1">Session ID: {sessionId}</p>}
        </header>

        {/* Message Display Area */}
        <div className="flex-grow p-4 space-y-4 overflow-y-auto bg-slate-700 custom-scrollbar">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${
                msg.sender === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={`max-w-xs md:max-w-md lg:max-w-lg px-4 py-3 rounded-xl shadow ${
                  msg.sender === 'user'
                    ? 'bg-sky-600 text-white rounded-br-none'
                    : msg.isError
                    ? 'bg-red-500 text-white rounded-bl-none'
                    : 'bg-slate-600 text-slate-100 rounded-bl-none'
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
                <p className="text-xs text-right mt-1 opacity-70">
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  {msg.sender === 'bot' && msg.intent && <span className="ml-2 italic text-sky-300">({msg.intent})</span>}
                </p>
                 {msg.sender === 'bot' && msg.isEscalated && (
                  <p className="text-xs text-amber-400 mt-1">
                    Escalated! Ticket: {msg.escalationTicketId || 'N/A'}
                  </p>
                )}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="px-4 py-3 rounded-xl shadow bg-slate-600 text-slate-100 rounded-bl-none">
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-sky-400 rounded-full animate-pulse delay-75"></div>
                  <div className="w-2 h-2 bg-sky-400 rounded-full animate-pulse delay-150"></div>
                  <div className="w-2 h-2 bg-sky-400 rounded-full animate-pulse delay-300"></div>
                  <span className="text-sm text-slate-300">Bot is typing...</span>
                </div>
              </div>
            </div>
          )}
          {error && (
             <div className="flex justify-center">
                <p className="text-sm text-red-400 bg-red-900 bg-opacity-50 px-3 py-2 rounded-md">{error}</p>
             </div>
          )}
          <div ref={messagesEndRef} /> {/* Anchor for scrolling */}
        </div>

        {/* Feedback Section */}
        {showFeedback && lastBotMessageForFeedback && (
          <div className="p-3 border-t border-slate-600 bg-slate-700">
            <p className="text-sm text-slate-300 mb-2">How helpful was that last response?</p>
            <div className="flex items-center space-x-2 mb-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  onClick={() => setCurrentRating(star)}
                  className={`text-2xl transition-colors duration-150 ${
                    currentRating >= star ? 'text-yellow-400' : 'text-slate-500 hover:text-yellow-300'
                  }`}
                  aria-label={`Rate ${star} star`}
                >
                  ★
                </button>
              ))}
            </div>
            {currentRating > 0 && (
                 <textarea
                    value={feedbackComment}
                    onChange={(e) => setFeedbackComment(e.target.value)}
                    placeholder="Optional: Add a comment..."
                    rows="2"
                    className="w-full p-2 rounded-md bg-slate-600 text-slate-100 border border-slate-500 focus:ring-1 focus:ring-sky-500 focus:border-sky-500 placeholder-slate-400 text-sm"
                />
            )}
            <button
              onClick={handleFeedbackSubmit}
              disabled={isLoading || currentRating === 0}
              className="mt-2 w-full px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-500 text-white rounded-md transition-colors duration-150 text-sm font-medium"
            >
              Submit Feedback
            </button>
          </div>
        )}


        {/* Input Area */}
        <div className="p-4 bg-slate-800 rounded-b-lg shadow-inner">
          <div className="flex items-center space-x-2">
            <input
              type="text"
              value={inputValue}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              className="flex-grow p-3 rounded-lg bg-slate-600 text-slate-100 placeholder-slate-400 focus:ring-2 focus:ring-sky-500 focus:border-transparent outline-none transition-shadow"
              disabled={isLoading}
            />
            <button
              onClick={handleSendMessage}
              disabled={isLoading || inputValue.trim() === ''}
              className="px-6 py-3 bg-sky-600 hover:bg-sky-700 disabled:bg-sky-800 disabled:text-slate-400 text-white font-semibold rounded-lg transition-colors duration-150 shadow hover:shadow-md focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-800"
              aria-label="Send message"
            >
              Send
            </button>
          </div>
        </div>
      </div>
      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #475569; // slate-600
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #334155; // slate-700
        }
        /* For Firefox */
        .custom-scrollbar {
          scrollbar-width: thin;
          scrollbar-color: #475569 transparent; // slate-600 and track color
        }
      `}</style>
    </div>
  );
}

export default App;
