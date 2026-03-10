import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Menu, X, User, LogOut, Plus, Bell } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';
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
  const [unread, setUnread] = useState(0);
  const [notifs, setNotifs] = useState([]);

  const fetchNotifs = useCallback(async () => {
    if (!user) return;
    try {
      const res = await api.get('/notificaciones');
      setUnread(res.data.unread_count);
      setNotifs(res.data.notifications?.slice(0, 5) || []);
    } catch { /* ignore */ }
  }, [user]);

  useEffect(() => {
    fetchNotifs();
    const i = setInterval(fetchNotifs, 15000);
    return () => clearInterval(i);
  }, [fetchNotifs]);

  const markAllRead = async () => {
    try {
      await api.put('/notificaciones/leer-todas');
      setUnread(0);
      setNotifs(n => n.map(x => ({ ...x, read: true })));
    } catch { /* ignore */ }
  };

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
            <Link to="/" className="text-slate-600 hover:text-[#18b29c] font-medium transition-colors" data-testid="nav-comprar">Comprar</Link>
            <Link to="/vender" className="text-slate-600 hover:text-[#18b29c] font-medium transition-colors" data-testid="nav-vender">Vender</Link>
            <Link to="/?canarias=true" className="text-slate-600 hover:text-[#18b29c] font-medium transition-colors" data-testid="nav-canarias">Solo Canarias</Link>
            <a href="/#ayuda" className="text-slate-600 hover:text-[#18b29c] font-medium transition-colors" data-testid="nav-ayuda">Ayuda</a>
          </nav>

          <div className="flex items-center gap-2">
            {user ? (
              <>
                <Button onClick={() => navigate('/vender')} className="hidden md:flex bg-[#18b29c] hover:bg-[#149682] text-white rounded-full px-5" data-testid="header-sell-btn">
                  <Plus className="w-4 h-4 mr-1" /> Vender
                </Button>

                {/* Notifications Bell */}
                <DropdownMenu onOpenChange={(open) => { if (open) fetchNotifs(); }}>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="rounded-full w-10 h-10 p-0 relative" data-testid="header-notifications-btn">
                      <Bell className="w-5 h-5 text-slate-600" />
                      {unread > 0 && (
                        <span className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                          {unread > 9 ? '9+' : unread}
                        </span>
                      )}
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-80 rounded-xl max-h-96 overflow-y-auto">
                    <div className="flex items-center justify-between px-3 py-2 border-b">
                      <span className="font-bold text-sm text-slate-800">Notificaciones</span>
                      {unread > 0 && (
                        <button onClick={markAllRead} className="text-xs text-[#18b29c] hover:underline" data-testid="mark-all-read-btn">Marcar todo leido</button>
                      )}
                    </div>
                    {notifs.length > 0 ? notifs.map((n) => (
                      <DropdownMenuItem key={n.id} className={`cursor-pointer px-3 py-2.5 ${!n.read ? 'bg-[#18b29c]/5' : ''}`} onClick={() => navigate(`/subasta/${n.auction_id}`)} data-testid={`notif-${n.id}`}>
                        <div className="flex-1 min-w-0">
                          <p className={`text-sm leading-snug ${!n.read ? 'font-semibold text-slate-800' : 'text-slate-600'}`}>{n.message}</p>
                          <p className="text-xs text-slate-400 mt-0.5">{new Date(n.created_at).toLocaleString('es-ES')}</p>
                        </div>
                        {!n.read && <div className="w-2 h-2 bg-[#18b29c] rounded-full flex-shrink-0 ml-2" />}
                      </DropdownMenuItem>
                    )) : (
                      <div className="px-3 py-6 text-center text-slate-400 text-sm">Sin notificaciones</div>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>

                {/* User Menu */}
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
                      <LogOut className="w-4 h-4 mr-2" /> Cerrar Sesion
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            ) : (
              <div className="hidden md:flex items-center gap-2">
                <Button variant="ghost" onClick={() => navigate('/auth?tab=login')} className="rounded-full text-slate-600" data-testid="header-login-btn">Entrar</Button>
                <Button onClick={() => navigate('/auth?tab=register')} className="bg-[#18b29c] hover:bg-[#149682] text-white rounded-full" data-testid="header-register-btn">Registrarse</Button>
              </div>
            )}

            <button className="md:hidden text-slate-600" onClick={() => setMobileOpen(!mobileOpen)} data-testid="mobile-menu-toggle">
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
