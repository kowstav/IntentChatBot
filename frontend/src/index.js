// frontend/src/index.js
import React from 'react';
import ReactDOM from 'react-dom';
import './index.css'; // Assuming you have a global CSS file
import App from './App'; // Your main App component
import reportWebVitals from './reportWebVitals';

ReactDOM.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
  document.getElementById('root')
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();