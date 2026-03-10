import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Edit, Gavel, Package, Loader2, LogOut, Heart, Trophy, Bell, Star, Crown, AlertTriangle, CreditCard, CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { AuctionCard } from '@/components/AuctionCard';
import { StarRating } from '@/components/StarRating';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function ProfilePage() {
  const { user, logout, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editName, setEditName] = useState('');
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [ratings, setRatings] = useState([]);
  const [disputes, setDisputes] = useState([]);

  useEffect(() => {
    if (!authLoading && !user) { navigate('/auth?tab=login'); return; }
    if (user) { fetchProfile(); fetchNotifications(); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, authLoading, navigate]);

  const fetchProfile = async () => {
    try {
      const res = await api.get(`/usuarios/${user.id}`);
      setProfile(res.data);
      setEditName(res.data.user?.name || '');
      setRatings(res.data.ratings || []);
      setDisputes(res.data.disputes || []);
    } catch { toast.error('Error al cargar perfil'); }
    finally { setLoading(false); }
  };

  const fetchNotifications = async () => {
    try {
      const res = await api.get('/notificaciones');
      setNotifications(res.data.notifications || []);
    } catch { /* ignore */ }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put(`/usuarios/${user.id}`, { name: editName });
      toast.success('Perfil actualizado');
      setEditing(false); fetchProfile();
    } catch { toast.error('Error al actualizar'); }
    finally { setSaving(false); }
  };

  const markRead = async (id) => {
    await api.put(`/notificaciones/${id}/leer`);
    setNotifications(n => n.map(x => x.id === id ? { ...x, read: true } : x));
  };

  if (loading || authLoading) return <div className="min-h-screen bg-[#f5f7fa] flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-[#18b29c]" /></div>;
  if (!profile || !user) return null;

  const wonAuctions = profile.won_auctions || [];
  const favorites = profile.favorites || [];

  return (
    <div className="min-h-screen bg-[#f5f7fa] pb-20 md:pb-0" data-testid="profile-page">
      <div className="container mx-auto px-4 md:px-6 max-w-5xl py-8">
        <Card className="border-0 shadow-sm rounded-2xl mb-6"><CardContent className="p-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-[#18b29c] text-white flex items-center justify-center text-2xl font-extrabold flex-shrink-0" style={{ fontFamily: 'Nunito, sans-serif' }}>{profile.user?.name?.charAt(0).toUpperCase()}</div>
            <div className="flex-1 min-w-0">
              {editing ? (
                <div className="flex gap-2 flex-wrap">
                  <Input value={editName} onChange={(e) => setEditName(e.target.value)} className="rounded-xl max-w-xs" data-testid="profile-name-input" />
                  <Button onClick={handleSave} disabled={saving} className="bg-[#18b29c] text-white rounded-full" data-testid="profile-save-btn">{saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Guardar'}</Button>
                  <Button variant="ghost" onClick={() => setEditing(false)} className="rounded-full" data-testid="profile-cancel-btn">Cancelar</Button>
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-extrabold text-slate-800 truncate" style={{ fontFamily: 'Nunito, sans-serif' }} data-testid="profile-name">{profile.user?.name}</h1>
                  <button onClick={() => setEditing(true)} className="text-slate-400 hover:text-[#18b29c] transition-colors flex-shrink-0" data-testid="profile-edit-btn"><Edit className="w-4 h-4" /></button>
                </div>
              )}
              <p className="text-slate-500 text-sm mt-1" data-testid="profile-email">{profile.user?.email}</p>
              <div className="mt-1" data-testid="profile-rating">
                <StarRating rating={profile.rating_avg || 0} count={profile.rating_count || 0} size="sm" />
              </div>
              {profile.plan && profile.plan !== 'free' && (
                <Badge className={`mt-1 rounded-full text-xs border-0 ${profile.plan === 'pro' ? 'bg-[#ffb347]/10 text-[#ffb347]' : 'bg-[#18b29c]/10 text-[#18b29c]'}`} data-testid="profile-plan-badge">
                  {profile.plan === 'pro' ? <><Crown className="w-3 h-3 mr-1" />Pro</> : <><CreditCard className="w-3 h-3 mr-1" />Vendedor</>}
                </Badge>
              )}
              {profile.plan === 'pro' && (
                <Badge className="mt-1 bg-[#18b29c]/10 text-[#18b29c] border-0 rounded-full text-xs" data-testid="profile-verified-badge">
                  <CheckCircle className="w-3 h-3 mr-1" /> Vendedor verificado
                </Badge>
              )}
            </div>
            <Button variant="outline" onClick={() => navigate('/precios')} className="rounded-full flex-shrink-0" data-testid="profile-pricing-btn">
              <CreditCard className="w-4 h-4 mr-1" /> Planes
            </Button>
            <Button variant="outline" onClick={() => { logout(); navigate('/'); }} className="rounded-full flex-shrink-0" data-testid="profile-logout-btn">
              <LogOut className="w-4 h-4 mr-1" /> Cerrar sesion
            </Button>
          </div>
        </CardContent></Card>

        <Tabs defaultValue="auctions">
          <TabsList className="w-full grid grid-cols-7 rounded-xl mb-6" data-testid="profile-tabs">
            <TabsTrigger value="auctions" className="rounded-lg text-xs sm:text-sm" data-testid="profile-tab-auctions"><Package className="w-4 h-4 mr-1 hidden sm:block" /> Subastas</TabsTrigger>
            <TabsTrigger value="bids" className="rounded-lg text-xs sm:text-sm" data-testid="profile-tab-bids"><Gavel className="w-4 h-4 mr-1 hidden sm:block" /> Pujas</TabsTrigger>
            <TabsTrigger value="won" className="rounded-lg text-xs sm:text-sm" data-testid="profile-tab-won"><Trophy className="w-4 h-4 mr-1 hidden sm:block" /> Ganadas</TabsTrigger>
            <TabsTrigger value="favorites" className="rounded-lg text-xs sm:text-sm" data-testid="profile-tab-favorites"><Heart className="w-4 h-4 mr-1 hidden sm:block" /> Favoritos</TabsTrigger>
            <TabsTrigger value="ratings" className="rounded-lg text-xs sm:text-sm" data-testid="profile-tab-ratings"><Star className="w-4 h-4 mr-1 hidden sm:block" /> Valoraciones</TabsTrigger>
            <TabsTrigger value="disputes" className="rounded-lg text-xs sm:text-sm relative" data-testid="profile-tab-disputes">
              <AlertTriangle className="w-4 h-4 mr-1 hidden sm:block" /> Disputas
              {disputes.filter(d => d.status === 'open' || d.status === 'reviewing').length > 0 && <span className="absolute -top-1 -right-1 w-4 h-4 bg-orange-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center">{disputes.filter(d => d.status === 'open' || d.status === 'reviewing').length}</span>}
            </TabsTrigger>
            <TabsTrigger value="notifications" className="rounded-lg text-xs sm:text-sm relative" data-testid="profile-tab-notifications">
              <Bell className="w-4 h-4 mr-1 hidden sm:block" /> Avisos
              {notifications.filter(n => !n.read).length > 0 && <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center">{notifications.filter(n => !n.read).length}</span>}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="auctions">
            {profile.auctions?.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">{profile.auctions.map((a) => <AuctionCard key={a.id} auction={a} />)}</div>
            ) : (
              <div className="text-center py-16" data-testid="empty-auctions">
                <Package className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500 mb-4">Aun no has publicado ninguna subasta</p>
                <Button onClick={() => navigate('/vender')} className="bg-[#18b29c] text-white rounded-full" data-testid="profile-create-auction-btn">Publicar subasta</Button>
              </div>
            )}
          </TabsContent>

          <TabsContent value="bids">
            {profile.active_bids?.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">{profile.active_bids.map((a) => <AuctionCard key={a.id} auction={a} />)}</div>
            ) : (
              <div className="text-center py-16" data-testid="empty-bids">
                <Gavel className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500 mb-4">Aun no has pujado en ninguna subasta</p>
                <Button onClick={() => navigate('/')} className="bg-[#18b29c] text-white rounded-full" data-testid="profile-browse-btn">Explorar subastas</Button>
              </div>
            )}
          </TabsContent>

          <TabsContent value="won">
            {wonAuctions.length > 0 ? (
              <div className="space-y-4">
                {wonAuctions.map((a) => (
                  <Card key={a.id} className="border-0 shadow-sm rounded-2xl cursor-pointer hover:shadow-md transition-all" onClick={() => navigate(`/subasta/${a.id}`)} data-testid={`won-auction-${a.id}`}>
                    <CardContent className="p-4 flex items-center gap-4">
                      <img src={a.images?.[0]} alt={a.title} className="w-20 h-20 rounded-xl object-cover flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <h3 className="font-bold text-slate-800 truncate">{a.title}</h3>
                        <p className="text-[#18b29c] font-extrabold text-lg">{a.current_price.toFixed(2)} &euro;</p>
                        <p className="text-xs text-slate-400">{a.location}</p>
                      </div>
                      <div className="flex-shrink-0 text-right">
                        <Badge className="bg-[#18b29c] text-white border-0 rounded-full">Ganada</Badge>
                        <p className="text-xs text-slate-500 mt-1">Contacta al vendedor</p>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center py-16" data-testid="empty-won">
                <Trophy className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500 mb-4">Aun no has ganado ninguna subasta</p>
                <Button onClick={() => navigate('/')} className="bg-[#18b29c] text-white rounded-full">Explorar subastas</Button>
              </div>
            )}
          </TabsContent>

          <TabsContent value="favorites">
            {favorites.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">{favorites.map((a) => <AuctionCard key={a.id} auction={a} initialFavorited={true} />)}</div>
            ) : (
              <div className="text-center py-16" data-testid="empty-favorites">
                <Heart className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500 mb-4">Aun no tienes favoritos. Pulsa el corazon en las subastas que te interesen.</p>
                <Button onClick={() => navigate('/')} className="bg-[#18b29c] text-white rounded-full">Explorar subastas</Button>
              </div>
            )}
          </TabsContent>

          <TabsContent value="ratings">
            {ratings.length > 0 ? (
              <div className="space-y-3">
                <div className="bg-white rounded-2xl shadow-sm p-6 mb-4" data-testid="rating-summary">
                  <div className="flex items-center gap-4">
                    <div className="text-center">
                      <p className="text-4xl font-extrabold text-[#ffb347]" style={{ fontFamily: 'Nunito, sans-serif' }}>{(profile.rating_avg || 0).toFixed(1)}</p>
                      <StarRating rating={profile.rating_avg || 0} count={0} showCount={false} size="md" />
                      <p className="text-xs text-slate-500 mt-1">{profile.rating_count || 0} valoraciones</p>
                    </div>
                  </div>
                </div>
                {ratings.map((r) => (
                  <Card key={r.id} className="border-0 shadow-sm rounded-xl" data-testid={`rating-${r.id}`}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-600">{r.rater_name?.charAt(0).toUpperCase()}</div>
                          <div>
                            <p className="font-medium text-sm text-slate-800">{r.rater_name}</p>
                            <p className="text-xs text-slate-400">{new Date(r.created_at).toLocaleDateString('es-ES')}</p>
                          </div>
                        </div>
                        <StarRating rating={r.rating} count={0} showCount={false} size="sm" />
                      </div>
                      {r.comment && <p className="text-sm text-slate-600 mt-2 italic">"{r.comment}"</p>}
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center py-16" data-testid="empty-ratings">
                <Star className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500 mb-4">Aun no has recibido valoraciones</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="disputes">
            {disputes.length > 0 ? (
              <div className="space-y-3">
                {disputes.map((d) => {
                  const statusMap = { open: { cls: 'bg-orange-100 text-orange-700', label: 'Abierta' }, reviewing: { cls: 'bg-blue-100 text-blue-700', label: 'En revision' }, resolved_buyer: { cls: 'bg-green-100 text-green-700', label: 'Resuelta (comprador)' }, resolved_seller: { cls: 'bg-green-100 text-green-700', label: 'Resuelta (vendedor)' }, closed: { cls: 'bg-slate-100 text-slate-600', label: 'Cerrada' } };
                  const s = statusMap[d.status] || { cls: 'bg-slate-100', label: d.status };
                  return (
                    <Card key={d.id} className="border-0 shadow-sm rounded-xl" data-testid={`profile-dispute-${d.id}`}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <h3 className="font-bold text-sm text-slate-800">{d.auction_title}</h3>
                            <p className="text-xs text-slate-500">{d.reason}</p>
                            <p className="text-xs text-slate-400 mt-0.5">{new Date(d.created_at).toLocaleDateString('es-ES')}</p>
                          </div>
                          <Badge className={`${s.cls} border-0 rounded-full text-xs`}>{s.label}</Badge>
                        </div>
                        <p className="text-xs text-slate-600">{d.description}</p>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-16" data-testid="empty-disputes">
                <AlertTriangle className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500">No tienes disputas</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="notifications">
            {notifications.length > 0 ? (
              <div className="space-y-3">
                {notifications.map((n) => (
                  <Card key={n.id} className={`border-0 shadow-sm rounded-xl cursor-pointer hover:shadow-md transition-all ${!n.read ? 'ring-2 ring-[#18b29c]/20 bg-[#18b29c]/5' : ''}`}
                    onClick={() => { markRead(n.id); navigate(`/subasta/${n.auction_id}`); }} data-testid={`notification-${n.id}`}>
                    <CardContent className="p-4 flex items-start gap-3">
                      <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${!n.read ? 'bg-[#18b29c]' : 'bg-transparent'}`} />
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm ${!n.read ? 'font-semibold text-slate-800' : 'text-slate-600'}`}>{n.message}</p>
                        <p className="text-xs text-slate-400 mt-1">{new Date(n.created_at).toLocaleString('es-ES')}</p>
                      </div>
                      {n.type === 'auction_won' && <Badge className="bg-[#18b29c] text-white border-0 rounded-full text-xs flex-shrink-0">Ganada</Badge>}
                      {n.type === 'outbid' && <Badge className="bg-[#ffb347] text-white border-0 rounded-full text-xs flex-shrink-0">Superada</Badge>}
                      {n.type === 'auction_cancelled' && <Badge variant="destructive" className="rounded-full text-xs flex-shrink-0">Cancelada</Badge>}
                      {n.type === 'message' && <Badge className="bg-blue-500 text-white border-0 rounded-full text-xs flex-shrink-0">Mensaje</Badge>}
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center py-16" data-testid="empty-notifications">
                <Bell className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500">Sin notificaciones por ahora</p>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
