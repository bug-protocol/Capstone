import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Auth from './pages/Auth';
import DashboardLayout from './pages/DashboardLayout';
import Chat from './pages/Chat';
import AdverseEvents from './pages/AdverseEvents';
import TriageCases from './pages/TriageCases';

const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/auth" />;
  }
  return children;
};

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/auth" element={<Auth />} />
        
        {/* Protected Dashboard Layout */}
        <Route 
          path="/" 
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          } 
        >
          {/* Nested Routes inside Dashboard */}
          <Route index element={<Chat />} />
          <Route path="chat/:sessionId" element={<Chat />} />
          <Route path="adverse-events" element={<AdverseEvents />} />
          <Route path="triage-cases" element={<TriageCases />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
