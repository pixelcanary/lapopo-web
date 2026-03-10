import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users, ShoppingCart, Gavel, BarChart3, Trash2, Loader2, Shield, XCircle, CheckCircle, Clock,
  ArrowLeft, Star, RefreshCw
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function AdminPage() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [auctions, setAuctions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(null);

  useEffect(() => {
    if (!authLoading && (!user || !user.is_admin)) {
      navigate('/');
      return;
    }
    if (user?.is_admin) fetchAll();
  }, [user, authLoading, navigate]);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [statsRes, usersRes, auctionsRes] = await Promise.all([
        api.get('/admin/stats'),
        api.get('/admin/usuarios'),
        api.get('/admin/subastas'),
      ]);
      setStats(statsRes.data);
      setUsers(usersRes.data);
      setAuctions(auctionsRes.data);
    } catch (err) {
      toast.error('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  const deleteUser = async (userId, userName) => {
    if (!window.confirm(`Eliminar al usuario "${userName}"? Sus subastas activas seran canceladas.`)) return;
    setDeleting(userId);
    try {
      await api.delete(`/admin/usuarios/${userId}`);
      toast.success('Usuario eliminado');
      fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    } finally {
      setDeleting(null);
    }
  };

  const deleteAuction = async (auctionId, title) => {
    if (!window.confirm(`Eliminar la subasta "${title}"?`)) return;
    setDeleting(auctionId);
    try {
      await api.delete(`/admin/subastas/${auctionId}`);
      toast.success('Subasta eliminada');
      fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    } finally {
      setDeleting(null);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-[#f5f7fa] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[#18b29c]" />
      </div>
    );
  }

  if (!user?.is_admin) return null;

  const statusBadge = (status) => {
    if (status === 'active') return <Badge className="bg-[#18b29c] text-white border-0 rounded-full text-xs" data-testid="badge-active"><CheckCircle className="w-3 h-3 mr-1" />Activa</Badge>;
    if (status === 'finished') return <Badge className="bg-slate-500 text-white border-0 rounded-full text-xs" data-testid="badge-finished"><Clock className="w-3 h-3 mr-1" />Finalizada</Badge>;
    if (status === 'cancelled') return <Badge variant="destructive" className="rounded-full text-xs" data-testid="badge-cancelled"><XCircle className="w-3 h-3 mr-1" />Cancelada</Badge>;
    return <Badge variant="outline" className="rounded-full text-xs">{status}</Badge>;
  };

  return (
    <div className="min-h-screen bg-[#f5f7fa] pb-20 md:pb-0" data-testid="admin-page">
      <div className="container mx-auto px-4 md:px-6 max-w-6xl py-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/')} className="text-slate-400 hover:text-[#18b29c]" data-testid="admin-back">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <Shield className="w-6 h-6 text-[#18b29c]" />
              <h1 className="text-2xl font-extrabold text-slate-800" style={{ fontFamily: 'Nunito, sans-serif' }} data-testid="admin-title">
                Panel de Administracion
              </h1>
            </div>
          </div>
          <Button variant="outline" onClick={fetchAll} className="rounded-full" data-testid="admin-refresh">
            <RefreshCw className="w-4 h-4 mr-1" /> Actualizar
          </Button>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6" data-testid="admin-stats">
            {[
              { label: 'Usuarios', value: stats.total_users, icon: Users, color: '#18b29c' },
              { label: 'Activas', value: stats.active_auctions, icon: ShoppingCart, color: '#18b29c' },
              { label: 'Finalizadas', value: stats.finished_auctions, icon: CheckCircle, color: '#6b7280' },
              { label: 'Canceladas', value: stats.cancelled_auctions, icon: XCircle, color: '#ef4444' },
              { label: 'Total pujas', value: stats.total_bids, icon: Gavel, color: '#ffb347' },
              { label: 'Valoraciones', value: stats.total_ratings, icon: Star, color: '#ffb347' },
            ].map((s) => (
              <Card key={s.label} className="border-0 shadow-sm rounded-xl" data-testid={`stat-${s.label.toLowerCase()}`}>
                <CardContent className="p-4 text-center">
                  <s.icon className="w-5 h-5 mx-auto mb-1" style={{ color: s.color }} />
                  <p className="text-2xl font-extrabold text-slate-800" style={{ fontFamily: 'Nunito, sans-serif' }}>{s.value}</p>
                  <p className="text-xs text-slate-500">{s.label}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        <Tabs defaultValue="users">
          <TabsList className="w-full grid grid-cols-2 rounded-xl mb-6" data-testid="admin-tabs">
            <TabsTrigger value="users" className="rounded-lg" data-testid="admin-tab-users">
              <Users className="w-4 h-4 mr-1" /> Usuarios ({users.length})
            </TabsTrigger>
            <TabsTrigger value="auctions" className="rounded-lg" data-testid="admin-tab-auctions">
              <ShoppingCart className="w-4 h-4 mr-1" /> Subastas ({auctions.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="users">
            <Card className="border-0 shadow-sm rounded-2xl">
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full" data-testid="admin-users-table">
                    <thead>
                      <tr className="border-b border-slate-100 text-left">
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase">Usuario</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase">Email</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase text-center">Subastas</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase text-center">Rating</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase text-center">Rol</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase text-center">Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map((u) => (
                        <tr key={u.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors" data-testid={`user-row-${u.id}`}>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 rounded-full bg-[#18b29c] text-white flex items-center justify-center text-xs font-bold flex-shrink-0">
                                {u.name?.charAt(0).toUpperCase()}
                              </div>
                              <span className="font-medium text-sm text-slate-800">{u.name}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-600">{u.email}</td>
                          <td className="px-4 py-3 text-sm text-slate-600 text-center">{u.auction_count || 0}</td>
                          <td className="px-4 py-3 text-sm text-center">
                            <div className="flex items-center justify-center gap-1">
                              <Star className={`w-3 h-3 ${u.rating_avg > 0 ? 'text-[#ffb347] fill-[#ffb347]' : 'text-slate-300'}`} />
                              <span className="text-slate-600">{u.rating_avg?.toFixed(1) || '0.0'}</span>
                              <span className="text-slate-400 text-xs">({u.rating_count || 0})</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-center">
                            {u.is_admin ? (
                              <Badge className="bg-purple-100 text-purple-700 border-0 rounded-full text-xs">Admin</Badge>
                            ) : (
                              <Badge variant="outline" className="rounded-full text-xs">Usuario</Badge>
                            )}
                          </td>
                          <td className="px-4 py-3 text-center">
                            {!u.is_admin && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => deleteUser(u.id, u.name)}
                                disabled={deleting === u.id}
                                className="text-red-500 hover:text-red-700 hover:bg-red-50 rounded-full"
                                data-testid={`delete-user-${u.id}`}
                              >
                                {deleting === u.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                              </Button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="auctions">
            <Card className="border-0 shadow-sm rounded-2xl">
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full" data-testid="admin-auctions-table">
                    <thead>
                      <tr className="border-b border-slate-100 text-left">
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase">Subasta</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase">Vendedor</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase text-center">Precio</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase text-center">Pujas</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase text-center">Estado</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase text-center">Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auctions.map((a) => (
                        <tr key={a.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors" data-testid={`auction-row-${a.id}`}>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate(`/subasta/${a.id}`)}>
                              <img src={a.images?.[0] || ''} alt="" className="w-10 h-10 rounded-lg object-cover flex-shrink-0" />
                              <div className="min-w-0">
                                <p className="font-medium text-sm text-slate-800 truncate max-w-[200px] hover:text-[#18b29c] transition-colors">{a.title}</p>
                                <p className="text-xs text-slate-400">{a.location}</p>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-600">{a.seller_name}</td>
                          <td className="px-4 py-3 text-sm text-center font-bold text-[#18b29c]">{a.current_price?.toFixed(2)} &euro;</td>
                          <td className="px-4 py-3 text-sm text-center text-slate-600">{a.bid_count}</td>
                          <td className="px-4 py-3 text-center">{statusBadge(a.status)}</td>
                          <td className="px-4 py-3 text-center">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => deleteAuction(a.id, a.title)}
                              disabled={deleting === a.id}
                              className="text-red-500 hover:text-red-700 hover:bg-red-50 rounded-full"
                              data-testid={`delete-auction-${a.id}`}
                            >
                              {deleting === a.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
