import { Link, useLocation } from 'react-router-dom';
import { Home, Search, PlusCircle, User } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

export function MobileNav() {
  const location = useLocation();
  const { user } = useAuth();
  const path = location.pathname;

  const items = [
    { icon: Home, label: 'Inicio', to: '/' },
    { icon: Search, label: 'Buscar', to: '/' },
    { icon: PlusCircle, label: 'Vender', to: user ? '/vender' : '/auth?tab=login' },
    { icon: User, label: 'Perfil', to: user ? '/perfil' : '/auth?tab=login' },
  ];

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-slate-200 safe-area-bottom" data-testid="mobile-nav">
      <div className="flex items-center justify-around h-16 px-2">
        {items.map((item) => {
          const active = item.to === path;
          return (
            <Link
              key={item.label}
              to={item.to}
              className={`flex flex-col items-center gap-0.5 px-3 py-1 rounded-xl transition-colors ${
                active ? 'text-[#18b29c]' : 'text-slate-400 hover:text-slate-600'
              }`}
              data-testid={`mobile-nav-${item.label.toLowerCase()}`}
            >
              <item.icon className="w-5 h-5" />
              <span className="text-[10px] font-medium">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
