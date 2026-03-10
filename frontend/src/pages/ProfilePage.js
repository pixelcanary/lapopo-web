import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Edit, Gavel, Package, Loader2, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AuctionCard } from '@/components/AuctionCard';
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

  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/auth?tab=login');
      return;
    }
    if (user) fetchProfile();
  }, [user, authLoading, navigate]);

  const fetchProfile = async () => {
    try {
      const res = await api.get(`/usuarios/${user.id}`);
      setProfile(res.data);
      setEditName(res.data.user?.name || '');
    } catch (err) {
      toast.error('Error al cargar perfil');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put(`/usuarios/${user.id}`, { name: editName });
      toast.success('Perfil actualizado');
      setEditing(false);
      fetchProfile();
    } catch (err) {
      toast.error('Error al actualizar');
    } finally {
      setSaving(false);
    }
  };

  if (loading || authLoading) {
    return (
      <div className="min-h-screen bg-[#f5f7fa] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[#18b29c]" />
      </div>
    );
  }

  if (!profile || !user) return null;

  return (
    <div className="min-h-screen bg-[#f5f7fa] pb-20 md:pb-0" data-testid="profile-page">
      <div className="container mx-auto px-4 md:px-6 max-w-5xl py-8">
        {/* Profile Header */}
        <Card className="border-0 shadow-sm rounded-2xl mb-6">
          <CardContent className="p-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
              <div
                className="w-16 h-16 rounded-full bg-[#18b29c] text-white flex items-center justify-center text-2xl font-extrabold flex-shrink-0"
                style={{ fontFamily: 'Nunito, sans-serif' }}
              >
                {profile.user?.name?.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                {editing ? (
                  <div className="flex gap-2 flex-wrap">
                    <Input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="rounded-xl max-w-xs"
                      data-testid="profile-name-input"
                    />
                    <Button onClick={handleSave} disabled={saving} className="bg-[#18b29c] text-white rounded-full" data-testid="profile-save-btn">
                      {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Guardar'}
                    </Button>
                    <Button variant="ghost" onClick={() => setEditing(false)} className="rounded-full" data-testid="profile-cancel-btn">
                      Cancelar
                    </Button>
                  </div>
                ) : (
                  <div className="flex items-center gap-3">
                    <h1
                      className="text-2xl font-extrabold text-slate-800 truncate"
                      style={{ fontFamily: 'Nunito, sans-serif' }}
                      data-testid="profile-name"
                    >
                      {profile.user?.name}
                    </h1>
                    <button
                      onClick={() => setEditing(true)}
                      className="text-slate-400 hover:text-[#18b29c] transition-colors flex-shrink-0"
                      data-testid="profile-edit-btn"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                  </div>
                )}
                <p className="text-slate-500 text-sm mt-1" data-testid="profile-email">{profile.user?.email}</p>
              </div>
              <Button
                variant="outline"
                onClick={() => { logout(); navigate('/'); }}
                className="rounded-full flex-shrink-0"
                data-testid="profile-logout-btn"
              >
                <LogOut className="w-4 h-4 mr-1" /> Cerrar sesi&oacute;n
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Tabs */}
        <Tabs defaultValue="auctions">
          <TabsList className="w-full grid grid-cols-2 rounded-xl mb-6" data-testid="profile-tabs">
            <TabsTrigger value="auctions" className="rounded-lg" data-testid="profile-tab-auctions">
              <Package className="w-4 h-4 mr-2" /> Mis Subastas ({profile.auctions?.length || 0})
            </TabsTrigger>
            <TabsTrigger value="bids" className="rounded-lg" data-testid="profile-tab-bids">
              <Gavel className="w-4 h-4 mr-2" /> Mis Pujas ({profile.active_bids?.length || 0})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="auctions">
            {profile.auctions?.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {profile.auctions.map((auction) => (
                  <AuctionCard key={auction.id} auction={auction} />
                ))}
              </div>
            ) : (
              <div className="text-center py-16" data-testid="empty-auctions">
                <Package className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500 mb-4">A&uacute;n no has publicado ninguna subasta</p>
                <Button
                  onClick={() => navigate('/vender')}
                  className="bg-[#18b29c] text-white rounded-full"
                  data-testid="profile-create-auction-btn"
                >
                  Publicar subasta
                </Button>
              </div>
            )}
          </TabsContent>

          <TabsContent value="bids">
            {profile.active_bids?.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {profile.active_bids.map((auction) => (
                  <AuctionCard key={auction.id} auction={auction} />
                ))}
              </div>
            ) : (
              <div className="text-center py-16" data-testid="empty-bids">
                <Gavel className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500 mb-4">A&uacute;n no has pujado en ninguna subasta</p>
                <Button
                  onClick={() => navigate('/')}
                  className="bg-[#18b29c] text-white rounded-full"
                  data-testid="profile-browse-btn"
                >
                  Explorar subastas
                </Button>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
