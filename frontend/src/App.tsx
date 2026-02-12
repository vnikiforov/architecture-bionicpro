import React from 'react';
import { Auth0Provider } from '@auth0/auth0-react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { authConfig } from './auth/config';
import ReportPage from './components/ReportPage';
import Callback from './components/Callback';
import PrivateRoute from './components/PrivateRoute';

function App() {
  return (
    <Auth0Provider {...authConfig}>
      <Router>
        <Routes>
          <Route path="/callback" element={<Callback />} />
          <Route path="/" element={
            <PrivateRoute>
              <ReportPage />
            </PrivateRoute>
          } />
        </Routes>
      </Router>
    </Auth0Provider>
  );
}

export default App;