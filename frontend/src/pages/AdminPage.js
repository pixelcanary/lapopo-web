import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users, ShoppingCart, Gavel, Trash2, Loader2, Shield, XCircle, CheckCircle, Clock,
  ArrowLeft, Star, RefreshCw, AlertTriangle, CreditCard, ToggleLeft, ToggleRight, MessageCircle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function AdminPage() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [auctions, setAuctions] = useState([]);
  const [disputes, setDisputes] = useState([]);
  const [config, setConfig] = useState({ payments_enabled: false });
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(null);
  const [updatingDispute, setUpdatingDispute] = useState(null);
  const [togglingPayments, setTogglingPayments] = useState(false);

  useEffect(() => {
    if (!authLoading && (!user || !user.is_admin)) { navigate('/'); return; }
    if (user?.is_admin) fetchAll();
  }, [user, authLoading, navigate]);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [statsRes, usersRes, auctionsRes, disputesRes, configRes] = await Promise.all([
        api.get('/admin/stats'), api.get('/admin/usuarios'), api.get('/admin/subastas'),
        api.get('/admin/disputas'), api.get('/admin/config'),
      ]);
      setStats(statsRes.data); setUsers(usersRes.data); setAuctions(auctionsRes.data);
      setDisputes(disputesRes.data); setConfig(configRes.data);
    } catch { toast.error('Error al cargar datos'); }
    finally { setLoading(false); }
  };

  const deleteUser = async (userId, userName) => {
    if (!window.confirm(`Eliminar al usuario "${userName}"?`)) return;
    setDeleting(userId);
    try { await api.delete(`/admin/usuarios/${userId}`); toast.success('Usuario eliminado'); fetchAll(); }
    catch (err) { toast.error(err.response?.data?.detail || 'Error'); }
    finally { setDeleting(null); }
  };

  const deleteAuction = async (auctionId, title) => {
    if (!window.confirm(`Eliminar la subasta "${title}"?`)) return;
    setDeleting(auctionId);
    try { await api.delete(`/admin/subastas/${auctionId}`); toast.success('Subasta eliminada'); fetchAll(); }
    catch (err) { toast.error(err.response?.data?.detail || 'Error'); }
    finally { setDeleting(null); }
  };

  const togglePayments = async () => {
    setTogglingPayments(true);
    try {
      await api.put('/admin/config', { payments_enabled: !config.payments_enabled });
      setConfig(prev => ({ ...prev, payments_enabled: !prev.payments_enabled }));
      toast.success(`Pagos ${!config.payments_enabled ? 'activados' : 'desactivados'}`);
    } catch { toast.error('Error'); }
    finally { setTogglingPayments(false); }
  };

  const updateDisputeStatus = async (disputeId, newStatus) => {
    setUpdatingDispute(disputeId);
    try {
      await api.put(`/admin/disputas/${disputeId}/estado`, { status: newStatus });
      toast.success('Disputa actualizada');
      fetchAll();
    } catch (err) { toast.error(err.response?.data?.detail || 'Error'); }
    finally { setUpdatingDispute(null); }
  };

  if (authLoading || loading) return <div className="min-h-screen bg-[#f5f7fa] flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-[#18b29c]" /></div>;
  if (!user?.is_admin) return null;

  const statusBadge = (status) => {
    const map = {
      active: { cls: 'bg-[#18b29c] text-white', icon: CheckCircle, label: 'Activa' },
      finished: { cls: 'bg-slate-500 text-white', icon: Clock, label: 'Finalizada' },
      cancelled: { cls: 'bg-red-500 text-white', icon: XCircle, label: 'Cancelada' },
    };
    const s = map[status] || { cls: 'bg-slate-200', icon: Clock, label: status };
    return <Badge className={`${s.cls} border-0 rounded-full text-xs`}><s.icon className="w-3 h-3 mr-1" />{s.label}</Badge>;
  };

  const disputeStatusBadge = (status) => {
    const map = {
      open: { cls: 'bg-orange-100 text-orange-700', label: 'Abierta' },
      reviewing: { cls: 'bg-blue-100 text-blue-700', label: 'En revision' },
      resolved_buyer: { cls: 'bg-green-100 text-green-700', label: 'Resuelta (comprador)' },
      resolved_seller: { cls: 'bg-green-100 text-green-700', label: 'Resuelta (vendedor)' },
      closed: { cls: 'bg-slate-100 text-slate-600', label: 'Cerrada' },
    };
    const s = map[status] || { cls: 'bg-slate-100', label: status };
    return <Badge className={`${s.cls} border-0 rounded-full text-xs`}>{s.label}</Badge>;
  };

  const openDisputes = disputes.filter(d => d.status === 'open' || d.status === 'reviewing').length;

  return (
    <div className="min-h-screen bg-[#f5f7fa] pb-20 md:pb-0" data-testid="admin-page">
      <div className="container mx-auto px-4 md:px-6 max-w-6xl py-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/')} className="text-slate-400 hover:text-[#18b29c]" data-testid="admin-back"><ArrowLeft className="w-5 h-5" /></button>
            <Shield className="w-6 h-6 text-[#18b29c]" />
            <h1 className="text-2xl font-extrabold text-slate-800" style={{ fontFamily: 'Nunito, sans-serif' }} data-testid="admin-title">Panel de Administracion</h1>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" onClick={fetchAll} className="rounded-full" data-testid="admin-refresh"><RefreshCw className="w-4 h-4 mr-1" /> Actualizar</Button>
          </div>
        </div>

        {/* Payment toggle */}
        <Card className="border-0 shadow-sm rounded-2xl mb-6" data-testid="payment-toggle-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CreditCard className="w-5 h-5 text-[#18b29c]" />
              <div>
                <p className="font-bold text-sm text-slate-800">Sistema de pagos</p>
                <p className="text-xs text-slate-500">
                  {config.payments_enabled ? 'Los usuarios necesitan plan de pago para publicar mas de 5 subastas/mes' : 'Todo es gratis, sin limites de publicacion'}
                </p>
              </div>
            </div>
            <Button variant="ghost" onClick={togglePayments} disabled={togglingPayments} className="rounded-full" data-testid="toggle-payments-btn">
              {togglingPayments ? <Loader2 className="w-5 h-5 animate-spin" /> :
                config.payments_enabled ? <ToggleRight className="w-8 h-8 text-[#18b29c]" /> : <ToggleLeft className="w-8 h-8 text-slate-400" />
              }
            </Button>
          </CardContent>
        </Card>

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
          <TabsList className="w-full grid grid-cols-3 rounded-xl mb-6" data-testid="admin-tabs">
            <TabsTrigger value="users" className="rounded-lg" data-testid="admin-tab-users"><Users className="w-4 h-4 mr-1" /> Usuarios ({users.length})</TabsTrigger>
            <TabsTrigger value="auctions" className="rounded-lg" data-testid="admin-tab-auctions"><ShoppingCart className="w-4 h-4 mr-1" /> Subastas ({auctions.length})</TabsTrigger>
            <TabsTrigger value="disputes" className="rounded-lg relative" data-testid="admin-tab-disputes">
              <AlertTriangle className="w-4 h-4 mr-1" /> Disputas ({disputes.length})
              {openDisputes > 0 && <span className="absolute -top-1 -right-1 bg-orange-500 text-white text-[10px] w-4 h-4 rounded-full flex items-center justify-center">{openDisputes}</span>}
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
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase text-center">Plan</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase text-center">Rating</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase text-center">Rol</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase text-center">Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map((u) => (
                        <tr key={u.id} className="border-b border-slate-50 hover:bg-slate-50/50" data-testid={`user-row-${u.id}`}>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 rounded-full bg-[#18b29c] text-white flex items-center justify-center text-xs font-bold flex-shrink-0">{u.name?.charAt(0).toUpperCase()}</div>
                              <span className="font-medium text-sm text-slate-800">{u.name}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-600">{u.email}</td>
                          <td className="px-4 py-3 text-center">
                            <Badge className={`rounded-full text-xs border-0 ${u.plan === 'pro' ? 'bg-[#ffb347]/10 text-[#ffb347]' : u.plan === 'vendedor' ? 'bg-[#18b29c]/10 text-[#18b29c]' : 'bg-slate-100 text-slate-500'}`}>
                              {u.plan === 'pro' ? 'Pro' : u.plan === 'vendedor' ? 'Vendedor' : 'Gratis'}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-sm text-center">
                            <div className="flex items-center justify-center gap-1">
                              <Star className={`w-3 h-3 ${u.rating_avg > 0 ? 'text-[#ffb347] fill-[#ffb347]' : 'text-slate-300'}`} />
                              <span className="text-slate-600">{u.rating_avg?.toFixed(1) || '0.0'}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-center">
                            {u.is_admin ? <Badge className="bg-purple-100 text-purple-700 border-0 rounded-full text-xs">Admin</Badge> : <Badge variant="outline" className="rounded-full text-xs">Usuario</Badge>}
                          </td>
                          <td className="px-4 py-3 text-center">
                            {!u.is_admin && (
                              <Button variant="ghost" size="sm" onClick={() => deleteUser(u.id, u.name)} disabled={deleting === u.id} className="text-red-500 hover:text-red-700 hover:bg-red-50 rounded-full" data-testid={`delete-user-${u.id}`}>
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
                        <tr key={a.id} className="border-b border-slate-50 hover:bg-slate-50/50" data-testid={`auction-row-${a.id}`}>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate(`/subasta/${a.id}`)}>
                              <img src={a.images?.[0] || ''} alt="" className="w-10 h-10 rounded-lg object-cover flex-shrink-0" />
                              <div className="min-w-0"><p className="font-medium text-sm text-slate-800 truncate max-w-[200px] hover:text-[#18b29c]">{a.title}</p><p className="text-xs text-slate-400">{a.location}</p></div>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-600">{a.seller_name}</td>
                          <td className="px-4 py-3 text-sm text-center font-bold text-[#18b29c]">{a.current_price?.toFixed(2)} &euro;</td>
                          <td className="px-4 py-3 text-sm text-center text-slate-600">{a.bid_count}</td>
                          <td className="px-4 py-3 text-center">{statusBadge(a.status)}</td>
                          <td className="px-4 py-3 text-center">
                            <Button variant="ghost" size="sm" onClick={() => deleteAuction(a.id, a.title)} disabled={deleting === a.id} className="text-red-500 hover:text-red-700 hover:bg-red-50 rounded-full" data-testid={`delete-auction-${a.id}`}>
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

          <TabsContent value="disputes">
            {disputes.length > 0 ? (
              <div className="space-y-3">
                {disputes.map((d) => (
                  <Card key={d.id} className="border-0 shadow-sm rounded-xl" data-testid={`dispute-row-${d.id}`}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h3 className="font-bold text-sm text-slate-800">{d.auction_title}</h3>
                          <p className="text-xs text-slate-500">{d.reporter_name} vs {d.reported_name}</p>
                          <p className="text-xs text-slate-400 mt-0.5">{new Date(d.created_at).toLocaleDateString('es-ES')}</p>
                        </div>
                        {disputeStatusBadge(d.status)}
                      </div>
                      <div className="bg-slate-50 rounded-lg p-3 mb-3">
                        <p className="text-xs font-medium text-slate-600 mb-1">Motivo: {d.reason}</p>
                        <p className="text-xs text-slate-500">{d.description}</p>
                      </div>
                      {d.messages?.length > 0 && (
                        <div className="mb-3 space-y-1.5">
                          <p className="text-xs font-bold text-slate-500"><MessageCircle className="w-3 h-3 inline mr-1" />{d.messages.length} mensajes</p>
                          {d.messages.slice(-2).map((m, i) => (
                            <div key={i} className="text-xs bg-white border rounded-lg p-2">
                              <span className="font-medium">{m.sender_name}:</span> {m.content}
                            </div>
                          ))}
                        </div>
                      )}
                      {d.status !== 'closed' && (
                        <div className="flex flex-wrap gap-2">
                          {d.status === 'open' && (
                            <Button size="sm" onClick={() => updateDisputeStatus(d.id, 'reviewing')} disabled={updatingDispute === d.id} className="bg-blue-500 text-white rounded-full text-xs" data-testid={`dispute-review-${d.id}`}>
                              En revision
                            </Button>
                          )}
                          <Button size="sm" onClick={() => updateDisputeStatus(d.id, 'resolved_buyer')} disabled={updatingDispute === d.id} className="bg-green-500 text-white rounded-full text-xs" data-testid={`dispute-resolve-buyer-${d.id}`}>
                            Favor comprador
                          </Button>
                          <Button size="sm" onClick={() => updateDisputeStatus(d.id, 'resolved_seller')} disabled={updatingDispute === d.id} className="bg-green-500 text-white rounded-full text-xs" data-testid={`dispute-resolve-seller-${d.id}`}>
                            Favor vendedor
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => updateDisputeStatus(d.id, 'closed')} disabled={updatingDispute === d.id} className="rounded-full text-xs" data-testid={`dispute-close-${d.id}`}>
                            Cerrar
                          </Button>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center py-16" data-testid="no-disputes">
                <AlertTriangle className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500">No hay disputas</p>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
