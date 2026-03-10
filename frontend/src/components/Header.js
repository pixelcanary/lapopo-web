import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Menu, X, User, LogOut, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-slate-100" data-testid="header">
      <div className="container mx-auto px-4 md:px-6 max-w-7xl">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2" data-testid="header-logo">
            <span className="text-2xl font-extrabold text-[#18b29c]" style={{ fontFamily: 'Nunito, sans-serif' }}>
              Lapopo
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-6">
            <Link to="/" className="text-slate-600 hover:text-[#18b29c] font-medium transition-colors" data-testid="nav-comprar">
              Comprar
            </Link>
            <Link to="/vender" className="text-slate-600 hover:text-[#18b29c] font-medium transition-colors" data-testid="nav-vender">
              Vender
            </Link>
            <Link to="/?canarias=true" className="text-slate-600 hover:text-[#18b29c] font-medium transition-colors" data-testid="nav-canarias">
              Solo Canarias
            </Link>
            <a href="/#ayuda" className="text-slate-600 hover:text-[#18b29c] font-medium transition-colors" data-testid="nav-ayuda">
              Ayuda
            </a>
          </nav>

          <div className="flex items-center gap-3">
            {user ? (
              <>
                <Button
                  onClick={() => navigate('/vender')}
                  className="hidden md:flex bg-[#18b29c] hover:bg-[#149682] text-white rounded-full px-5"
                  data-testid="header-sell-btn"
                >
                  <Plus className="w-4 h-4 mr-1" /> Vender
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="rounded-full w-10 h-10 p-0" data-testid="header-user-menu">
                      <div className="w-8 h-8 rounded-full bg-[#18b29c] text-white flex items-center justify-center font-bold text-sm">
                        {user.name?.charAt(0).toUpperCase()}
                      </div>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48 rounded-xl">
                    <DropdownMenuItem onClick={() => navigate('/perfil')} data-testid="menu-profile" className="cursor-pointer">
                      <User className="w-4 h-4 mr-2" /> Mi Perfil
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => { logout(); navigate('/'); }} data-testid="menu-logout" className="cursor-pointer">
                      <LogOut className="w-4 h-4 mr-2" /> Cerrar Sesión
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            ) : (
              <div className="hidden md:flex items-center gap-2">
                <Button
                  variant="ghost"
                  onClick={() => navigate('/auth?tab=login')}
                  className="rounded-full text-slate-600"
                  data-testid="header-login-btn"
                >
                  Entrar
                </Button>
                <Button
                  onClick={() => navigate('/auth?tab=register')}
                  className="bg-[#18b29c] hover:bg-[#149682] text-white rounded-full"
                  data-testid="header-register-btn"
                >
                  Registrarse
                </Button>
              </div>
            )}

            <button
              className="md:hidden text-slate-600"
              onClick={() => setMobileOpen(!mobileOpen)}
              data-testid="mobile-menu-toggle"
            >
              {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {mobileOpen && (
          <div className="md:hidden pb-4 border-t border-slate-100 mt-2 pt-4 space-y-3 animate-in fade-in slide-in-from-top-2 duration-200">
            <Link to="/" onClick={() => setMobileOpen(false)} className="block text-slate-600 hover:text-[#18b29c] font-medium py-2">Comprar</Link>
            <Link to="/vender" onClick={() => setMobileOpen(false)} className="block text-slate-600 hover:text-[#18b29c] font-medium py-2">Vender</Link>
            <Link to="/?canarias=true" onClick={() => setMobileOpen(false)} className="block text-slate-600 hover:text-[#18b29c] font-medium py-2">Solo Canarias</Link>
            <a href="/#ayuda" onClick={() => setMobileOpen(false)} className="block text-slate-600 hover:text-[#18b29c] font-medium py-2">Ayuda</a>
            {!user && (
              <div className="flex gap-2 pt-2">
                <Button variant="outline" onClick={() => { navigate('/auth?tab=login'); setMobileOpen(false); }} className="rounded-full flex-1" data-testid="mobile-login-btn">Entrar</Button>
                <Button onClick={() => { navigate('/auth?tab=register'); setMobileOpen(false); }} className="bg-[#18b29c] text-white rounded-full flex-1" data-testid="mobile-register-btn">Registrarse</Button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
