import { Route, Routes } from 'react-router-dom';
import AssistantPage from './pages/AssistantPage';
import LandingPage from './pages/LandingPage';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/assistant" element={<AssistantPage />} />
    </Routes>
  );
}
