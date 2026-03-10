import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from '@/context/AuthContext';
import { Header } from '@/components/Header';
import { MobileNav } from '@/components/MobileNav';
import { Toaster } from 'sonner';
import HomePage from '@/pages/HomePage';
import AuthPage from '@/pages/AuthPage';
import CreateAuctionPage from '@/pages/CreateAuctionPage';
import AuctionDetailPage from '@/pages/AuctionDetailPage';
import ProfilePage from '@/pages/ProfilePage';
import '@/App.css';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="App">
          <Header />
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/auth" element={<AuthPage />} />
            <Route path="/vender" element={<CreateAuctionPage />} />
            <Route path="/subasta/:id" element={<AuctionDetailPage />} />
            <Route path="/perfil" element={<ProfilePage />} />
          </Routes>
          <MobileNav />
          <Toaster position="top-center" richColors />
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
