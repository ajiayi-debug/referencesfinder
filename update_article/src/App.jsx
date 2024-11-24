// src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Select from './pages/Select';
import Udecide from './pages/Udecide';
import FileViewer from './pages/FileViewer';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Select />} />
        <Route path="/udecide" element={<Udecide />} />
        <Route path="/fileviewer" element={<FileViewer />} /> 
      </Routes>
    </Router>
  );
}

export default App;
