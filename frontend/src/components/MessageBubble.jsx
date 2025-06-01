import React from 'react';
import styled from 'styled-components';

const BubbleWrapper = styled.div`
  display: flex;
  flex-direction: column;
  align-items: ${props => props.isUser ? 'flex-end' : 'flex-start'};
  margin: 10px;
`;

const Bubble = styled.div`
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 20px;
  background-color: ${props => props.isUser ? '#007bff' : '#f1f1f1'};
  color: ${props => props.isUser ? 'white' : 'black'};
  margin-bottom: 4px;
`;

const Timestamp = styled.span`
  font-size: 0.75rem;
  color: #666;
  margin: 2px 8px;
`;

const MessageBubble = ({ message }) => {
  const isUser = message.sender === 'user';
  const time = new Date(message.timestamp).toLocaleTimeString();

  return (
    <BubbleWrapper isUser={isUser}>
      <Bubble isUser={isUser}>
        {message.text}
        {message.intent && !isUser && (
          <div style={{ fontSize: '0.8em', marginTop: '4px', opacity: 0.7 }}>
            Intent: {message.intent}
          </div>
        )}
      </Bubble>
      <Timestamp>{time}</Timestamp>
    </BubbleWrapper>
  );
};

export default MessageBubble;