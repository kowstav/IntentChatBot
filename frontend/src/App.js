// frontend/src/App.js
import React from 'react';
import ChatWindow from './components/ChatWindow'; // Import the new ChatWindow component
// If you have global styles, import them here, e.g.:
// import './App.css';
// If using styled-components' ThemeProvider or global styles:
// import { ThemeProvider } from 'styled-components';
// import { GlobalStyle, theme } from './styles/theme'; // Example theme file

function App() {
  return (
    // <ThemeProvider theme={theme}> // Example if using a theme
    //   <GlobalStyle />             // Example for global styles
    <> {/* Or a main div with global app styling */}
      <ChatWindow />
    </>
    // </ThemeProvider>
  );
}

export default App;