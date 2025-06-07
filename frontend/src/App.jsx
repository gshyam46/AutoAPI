import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Button } from "./components/ui/button";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import UploadPage from "./pages/UploadPage";
import FileManagerPage from "./pages/FileManagerPage";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-100">
        <header className="bg-blue-600 text-white p-4">
          <h1>AutoAPI Ops</h1>
          <Button className="ml-4">Test Button</Button>
        </header>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/files" element={<FileManagerPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
