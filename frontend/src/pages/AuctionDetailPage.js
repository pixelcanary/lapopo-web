import { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, MapPin, User, Gavel, Hand, Package, Loader2, Tag } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Countdown } from '@/components/Countdown';
import { useAuth } from '@/context/AuthContext';
import api, { isCanarias } from '@/lib/api';
import { toast } from 'sonner';

const DELIVERY_LABELS = {
  pickup: 'Recogida en mano',
  shipping: 'Env\u00EDo',
  both: 'Env\u00EDo o recogida',
};

export default function AuctionDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [auction, setAuction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [bidAmount, setBidAmount] = useState('');
  const [bidding, setBidding] = useState(false);
  const [activeImage, setActiveImage] = useState(0);

  const fetchAuction = useCallback(async () => {
    try {
      const res = await api.get(`/subastas/${id}`);
      setAuction(res.data);
      if (!bidAmount || bidAmount === '') {
        setBidAmount((res.data.current_price + 0.50).toFixed(2));
      }
    } catch (err) {
      toast.error('Subasta no encontrada');
      navigate('/');
    } finally {
      setLoading(false);
    }
  }, [id, navigate, bidAmount]);

  useEffect(() => {
    fetchAuction();
    const interval = setInterval(fetchAuction, 10000);
    return () => clearInterval(interval);
  }, [fetchAuction]);

  const handleBid = async () => {
    if (!user) {
      navigate('/auth?tab=login');
      return;
    }
    setBidding(true);
    try {
      const res = await api.post(`/subastas/${id}/pujar`, { amount: parseFloat(bidAmount) });
      setAuction(res.data);
      setBidAmount((res.data.current_price + 0.50).toFixed(2));
      toast.success('Puja realizada correctamente');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al pujar');
    } finally {
      setBidding(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f5f7fa] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[#18b29c]" />
      </div>
    );
  }

  if (!auction) return null;

  const canarias = isCanarias(auction.location);
  const isOwner = user?.id === auction.seller_id;
  const isActive = auction.status === 'active';
  const minBid = auction.current_price + 0.50;

  return (
    <div className="min-h-screen bg-[#f5f7fa] pb-20 md:pb-0">
      <div className="container mx-auto px-4 md:px-6 max-w-6xl py-6">
        <Link to="/" className="flex items-center gap-2 mb-6 text-slate-500 hover:text-[#18b29c] transition-colors" data-testid="detail-back-link">
          <ArrowLeft className="w-4 h-4" /> Volver
        </Link>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Images */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-2xl overflow-hidden shadow-sm">
              <div className="aspect-[4/3] relative">
                <img
                  src={auction.images?.[activeImage] || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&q=80&w=600'}
                  alt={auction.title}
                  className="w-full h-full object-contain bg-slate-50"
                  data-testid="detail-main-image"
                />
                {canarias && (
                  <Badge className="absolute top-4 left-4 bg-[#ffb347] text-white border-0 rounded-full gap-1">
                    <Hand className="w-3 h-3" /> Canarias
                  </Badge>
                )}
              </div>
              {auction.images?.length > 1 && (
                <div className="flex gap-2 p-4 overflow-x-auto">
                  {auction.images.map((img, i) => (
                    <button
                      key={i}
                      onClick={() => setActiveImage(i)}
                      className={`w-16 h-16 rounded-lg overflow-hidden border-2 flex-shrink-0 transition-colors ${
                        i === activeImage ? 'border-[#18b29c]' : 'border-transparent hover:border-slate-300'
                      }`}
                      data-testid={`detail-thumb-${i}`}
                    >
                      <img src={img} alt="" className="w-full h-full object-cover" />
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Description */}
            <Card className="mt-4 border-0 shadow-sm rounded-2xl">
              <CardContent className="p-6">
                <h2 className="font-bold text-lg text-slate-800 mb-3">Descripci&oacute;n</h2>
                <p className="text-slate-600 leading-relaxed whitespace-pre-wrap" data-testid="detail-description">
                  {auction.description}
                </p>
              </CardContent>
            </Card>

            {/* Bid History */}
            <Card className="mt-4 border-0 shadow-sm rounded-2xl">
              <CardContent className="p-6">
                <h2 className="font-bold text-lg text-slate-800 mb-3" data-testid="bid-history-title">
                  Historial de pujas ({auction.bid_count})
                </h2>
                {auction.bids?.length > 0 ? (
                  <div className="space-y-3">
                    {[...auction.bids].reverse().map((bid, i) => (
                      <div key={bid.id || i} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-600">
                            {bid.user_name?.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <p className="font-medium text-sm text-slate-800">{bid.user_name}</p>
                            <p className="text-xs text-slate-400">{new Date(bid.timestamp).toLocaleString('es-ES')}</p>
                          </div>
                        </div>
                        <span className="font-bold text-[#18b29c]">{bid.amount.toFixed(2)} &euro;</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-400 text-sm" data-testid="no-bids-msg">A&uacute;n no hay pujas. &iexcl;S&eacute; el primero!</p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-2 space-y-4">
            <Card className="border-0 shadow-sm rounded-2xl sticky top-20">
              <CardContent className="p-6">
                <h1
                  className="text-xl md:text-2xl font-extrabold text-slate-800 mb-3"
                  style={{ fontFamily: 'Nunito, sans-serif' }}
                  data-testid="detail-title"
                >
                  {auction.title}
                </h1>
                <div className="flex items-center gap-2 mb-4">
                  <Countdown endTime={auction.end_time} />
                  {!isActive && <Badge variant="destructive" className="rounded-full">Finalizada</Badge>}
                </div>

                <Separator className="my-4" />

                <div className="mb-4">
                  <p className="text-sm text-slate-500 mb-1">Precio actual</p>
                  <p
                    className="text-4xl font-extrabold text-[#18b29c]"
                    style={{ fontFamily: 'Nunito, sans-serif' }}
                    data-testid="detail-current-price"
                  >
                    {auction.current_price.toFixed(2)} &euro;
                  </p>
                  <div className="flex items-center gap-3 mt-2 text-sm text-slate-500">
                    <span className="flex items-center gap-1"><Gavel className="w-3.5 h-3.5" />{auction.bid_count} pujas</span>
                    <span className="flex items-center gap-1"><Tag className="w-3.5 h-3.5" />Desde {auction.starting_price.toFixed(2)} &euro;</span>
                  </div>
                </div>

                {isActive && !isOwner && (
                  <div className="space-y-3">
                    <p className="text-sm text-slate-500">Tu puja (m&iacute;n. {minBid.toFixed(2)} &euro;)</p>
                    <div className="flex gap-2">
                      <Input
                        type="number"
                        min={minBid}
                        step={0.5}
                        value={bidAmount}
                        onChange={(e) => setBidAmount(e.target.value)}
                        className="rounded-xl"
                        data-testid="detail-bid-input"
                      />
                      <Button
                        onClick={handleBid}
                        disabled={bidding || parseFloat(bidAmount) < minBid}
                        className="bg-[#ffb347] hover:bg-[#ffa01a] text-white rounded-full px-6 font-bold shadow-md hover:shadow-lg active:scale-95 transition-all"
                        data-testid="detail-bid-btn"
                      >
                        {bidding ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Pujar'}
                      </Button>
                    </div>
                  </div>
                )}

                {isOwner && isActive && (
                  <div className="bg-[#18b29c]/10 rounded-xl p-4 text-sm text-[#18b29c] font-medium" data-testid="own-auction-msg">
                    Esta es tu subasta
                  </div>
                )}

                {!isActive && (
                  <div className="bg-slate-100 rounded-xl p-4 text-sm text-slate-600" data-testid="auction-ended-msg">
                    Esta subasta ha finalizado
                    {auction.bids?.length > 0 && (
                      <p className="font-bold mt-1">
                        Ganador: {auction.bids[auction.bids.length - 1]?.user_name} con {auction.current_price.toFixed(2)} &euro;
                      </p>
                    )}
                  </div>
                )}

                <Separator className="my-4" />

                <div className="space-y-3 text-sm">
                  <div className="flex items-center gap-2 text-slate-600">
                    <User className="w-4 h-4 text-slate-400" />
                    <span>Vendedor: <span className="font-medium">{auction.seller_name}</span></span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-600">
                    <MapPin className="w-4 h-4 text-slate-400" />
                    <span>{auction.location}</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-600">
                    <Package className="w-4 h-4 text-slate-400" />
                    <span>{DELIVERY_LABELS[auction.delivery_type] || auction.delivery_type}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
