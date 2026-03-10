import { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, MapPin, User, Gavel, Hand, Package, Loader2, Tag, ShoppingCart, XCircle, Zap, Send, Mail } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Countdown } from '@/components/Countdown';
import { useAuth } from '@/context/AuthContext';
import api, { isCanarias } from '@/lib/api';
import { toast } from 'sonner';

const DELIVERY_LABELS = { pickup: 'Recogida en mano', shipping: 'Envio', both: 'Envio o recogida' };

export default function AuctionDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [auction, setAuction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [bidAmount, setBidAmount] = useState('');
  const [bidding, setBidding] = useState(false);
  const [activeImage, setActiveImage] = useState(0);
  const [autoBidMax, setAutoBidMax] = useState('');
  const [settingAutoBid, setSettingAutoBid] = useState(false);
  const [showAutoBid, setShowAutoBid] = useState(false);
  const [contactInfo, setContactInfo] = useState(null);
  const [loadingContact, setLoadingContact] = useState(false);
  const [messages, setMessages] = useState([]);
  const [newMsg, setNewMsg] = useState('');
  const [sendingMsg, setSendingMsg] = useState(false);
  const [showMessages, setShowMessages] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [buyingNow, setBuyingNow] = useState(false);
  const [bidInit, setBidInit] = useState(false);

  const fetchAuction = useCallback(async () => {
    try {
      const res = await api.get(`/subastas/${id}`);
      setAuction(res.data);
      if (!bidInit) { setBidAmount((res.data.current_price + 0.50).toFixed(2)); setBidInit(true); }
    } catch { toast.error('Subasta no encontrada'); navigate('/'); }
    finally { setLoading(false); }
  }, [id, navigate, bidInit]);

  useEffect(() => { fetchAuction(); const i = setInterval(fetchAuction, 10000); return () => clearInterval(i); }, [fetchAuction]);

  const handleBid = async () => {
    if (!user) { navigate('/auth?tab=login'); return; }
    setBidding(true);
    try {
      const res = await api.post(`/subastas/${id}/pujar`, { amount: parseFloat(bidAmount) });
      setAuction(res.data); setBidAmount((res.data.current_price + 0.50).toFixed(2));
      toast.success('Puja realizada correctamente');
    } catch (err) { toast.error(err.response?.data?.detail || 'Error al pujar'); }
    finally { setBidding(false); }
  };

  const handleBuyNow = async () => {
    if (!user) { navigate('/auth?tab=login'); return; }
    setBuyingNow(true);
    try {
      const res = await api.post(`/subastas/${id}/comprar-ya`);
      setAuction(res.data);
      toast.success('Compra realizada. La subasta es tuya.');
    } catch (err) { toast.error(err.response?.data?.detail || 'Error al comprar'); }
    finally { setBuyingNow(false); }
  };

  const handleAutoBid = async () => {
    if (!user) { navigate('/auth?tab=login'); return; }
    setSettingAutoBid(true);
    try {
      const res = await api.post(`/subastas/${id}/auto-pujar`, { max_amount: parseFloat(autoBidMax) });
      toast.success(res.data.message);
      setShowAutoBid(false); setAutoBidMax('');
      fetchAuction();
    } catch (err) { toast.error(err.response?.data?.detail || 'Error'); }
    finally { setSettingAutoBid(false); }
  };

  const handleCancel = async () => {
    if (!window.confirm(auction.bid_count > 0 ? `Esta subasta tiene ${auction.bid_count} pujas. Los pujadores seran notificados. Seguro que quieres cancelarla?` : 'Seguro que quieres cancelar esta subasta?')) return;
    setCancelling(true);
    try {
      await api.post(`/subastas/${id}/cancelar`);
      toast.success('Subasta cancelada');
      fetchAuction();
    } catch (err) { toast.error(err.response?.data?.detail || 'Error al cancelar'); }
    finally { setCancelling(false); }
  };

  const fetchContact = async () => {
    setLoadingContact(true);
    try {
      const res = await api.get(`/contacto/${id}`);
      setContactInfo(res.data);
    } catch (err) { toast.error(err.response?.data?.detail || 'Error'); }
    finally { setLoadingContact(false); }
  };

  const fetchMessages = async () => {
    try { const res = await api.get(`/mensajes/${id}`); setMessages(res.data); } catch { /* ignore */ }
  };

  const sendMessage = async () => {
    if (!newMsg.trim()) return;
    const receiverId = user.id === auction.seller_id ? auction.winner_id : auction.seller_id;
    if (!receiverId) return;
    setSendingMsg(true);
    try {
      await api.post('/mensajes', { receiver_id: receiverId, auction_id: id, content: newMsg });
      setNewMsg(''); fetchMessages();
    } catch (err) { toast.error('Error al enviar'); }
    finally { setSendingMsg(false); }
  };

  if (loading) return <div className="min-h-screen bg-[#f5f7fa] flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-[#18b29c]" /></div>;
  if (!auction) return null;

  const canariasLoc = isCanarias(auction.location);
  const isOwner = user?.id === auction.seller_id;
  const isWinner = user?.id === auction.winner_id;
  const isActive = auction.status === 'active';
  const isFinished = auction.status === 'finished';
  const isCancelled = auction.status === 'cancelled';
  const minBid = auction.current_price + 0.50;
  const hasBuyNow = auction.buy_now_price && isActive;
  const canContact = isFinished && (isOwner || isWinner) && auction.winner_id;

  return (
    <div className="min-h-screen bg-[#f5f7fa] pb-20 md:pb-0">
      <div className="container mx-auto px-4 md:px-6 max-w-6xl py-6">
        <Link to="/" className="flex items-center gap-2 mb-6 text-slate-500 hover:text-[#18b29c] transition-colors" data-testid="detail-back-link"><ArrowLeft className="w-4 h-4" /> Volver</Link>
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Images */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-2xl overflow-hidden shadow-sm">
              <div className="aspect-[4/3] relative">
                <img src={auction.images?.[activeImage] || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&q=80&w=600'} alt={auction.title} className="w-full h-full object-contain bg-slate-50" data-testid="detail-main-image" />
                {canariasLoc && <Badge className="absolute top-4 left-4 bg-[#ffb347] text-white border-0 rounded-full gap-1"><Hand className="w-3 h-3" /> Canarias</Badge>}
                {isCancelled && <div className="absolute inset-0 bg-black/40 flex items-center justify-center"><span className="bg-red-500 text-white px-6 py-3 rounded-full font-bold text-lg">CANCELADA</span></div>}
              </div>
              {auction.images?.length > 1 && (
                <div className="flex gap-2 p-4 overflow-x-auto">
                  {auction.images.map((img, i) => (
                    <button key={i} onClick={() => setActiveImage(i)} className={`w-16 h-16 rounded-lg overflow-hidden border-2 flex-shrink-0 transition-colors ${i === activeImage ? 'border-[#18b29c]' : 'border-transparent hover:border-slate-300'}`} data-testid={`detail-thumb-${i}`}>
                      <img src={img} alt="" className="w-full h-full object-cover" />
                    </button>
                  ))}
                </div>
              )}
            </div>

            <Card className="mt-4 border-0 shadow-sm rounded-2xl"><CardContent className="p-6">
              <h2 className="font-bold text-lg text-slate-800 mb-3">Descripcion</h2>
              <p className="text-slate-600 leading-relaxed whitespace-pre-wrap" data-testid="detail-description">{auction.description}</p>
            </CardContent></Card>

            <Card className="mt-4 border-0 shadow-sm rounded-2xl"><CardContent className="p-6">
              <h2 className="font-bold text-lg text-slate-800 mb-3" data-testid="bid-history-title">Historial de pujas ({auction.bid_count})</h2>
              {auction.bids?.length > 0 ? (
                <div className="space-y-3">
                  {[...auction.bids].reverse().map((bid, i) => (
                    <div key={bid.id || i} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-600">{bid.user_name?.charAt(0).toUpperCase()}</div>
                        <div>
                          <p className="font-medium text-sm text-slate-800">{bid.user_name} {bid.auto && <span className="text-xs text-[#18b29c] ml-1">(auto)</span>} {bid.buy_now && <span className="text-xs text-[#ffb347] ml-1">(compra inmediata)</span>}</p>
                          <p className="text-xs text-slate-400">{new Date(bid.timestamp).toLocaleString('es-ES')}</p>
                        </div>
                      </div>
                      <span className="font-bold text-[#18b29c]">{bid.amount.toFixed(2)} &euro;</span>
                    </div>
                  ))}
                </div>
              ) : <p className="text-slate-400 text-sm" data-testid="no-bids-msg">Aun no hay pujas. Se el primero!</p>}
            </CardContent></Card>

            {/* Messages section for finished auctions */}
            {canContact && (
              <Card className="mt-4 border-0 shadow-sm rounded-2xl"><CardContent className="p-6">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-bold text-lg text-slate-800">Mensajes</h2>
                  <Button variant="outline" size="sm" onClick={() => { setShowMessages(!showMessages); if (!showMessages) fetchMessages(); }} className="rounded-full" data-testid="toggle-messages-btn">
                    <Send className="w-4 h-4 mr-1" /> {showMessages ? 'Ocultar' : 'Ver mensajes'}
                  </Button>
                </div>
                {showMessages && (
                  <div>
                    <div className="space-y-3 max-h-64 overflow-y-auto mb-4">
                      {messages.length > 0 ? messages.map((m) => (
                        <div key={m.id} className={`flex ${m.sender_id === user?.id ? 'justify-end' : 'justify-start'}`}>
                          <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 ${m.sender_id === user?.id ? 'bg-[#18b29c] text-white' : 'bg-slate-100 text-slate-800'}`}>
                            <p className="text-sm">{m.content}</p>
                            <p className={`text-[10px] mt-1 ${m.sender_id === user?.id ? 'text-white/60' : 'text-slate-400'}`}>{m.sender_name} - {new Date(m.created_at).toLocaleString('es-ES')}</p>
                          </div>
                        </div>
                      )) : <p className="text-slate-400 text-sm text-center py-4">Sin mensajes aun. Inicia la conversacion.</p>}
                    </div>
                    <div className="flex gap-2">
                      <Textarea value={newMsg} onChange={(e) => setNewMsg(e.target.value)} placeholder="Escribe un mensaje..." className="rounded-xl min-h-[44px] max-h-24" data-testid="message-input" />
                      <Button onClick={sendMessage} disabled={sendingMsg || !newMsg.trim()} className="bg-[#18b29c] text-white rounded-full px-4" data-testid="send-message-btn">
                        {sendingMsg ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent></Card>
            )}
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-2 space-y-4">
            <Card className="border-0 shadow-sm rounded-2xl sticky top-20"><CardContent className="p-6">
              <h1 className="text-xl md:text-2xl font-extrabold text-slate-800 mb-3" style={{ fontFamily: 'Nunito, sans-serif' }} data-testid="detail-title">{auction.title}</h1>
              <div className="flex items-center gap-2 mb-4 flex-wrap">
                <Countdown endTime={auction.end_time} />
                {isCancelled && <Badge variant="destructive" className="rounded-full">Cancelada</Badge>}
                {isFinished && <Badge variant="destructive" className="rounded-full">Finalizada</Badge>}
              </div>
              <Separator className="my-4" />

              <div className="mb-4">
                <p className="text-sm text-slate-500 mb-1">Precio actual</p>
                <p className="text-4xl font-extrabold text-[#18b29c]" style={{ fontFamily: 'Nunito, sans-serif' }} data-testid="detail-current-price">{auction.current_price.toFixed(2)} &euro;</p>
                <div className="flex items-center gap-3 mt-2 text-sm text-slate-500">
                  <span className="flex items-center gap-1"><Gavel className="w-3.5 h-3.5" />{auction.bid_count} pujas</span>
                  <span className="flex items-center gap-1"><Tag className="w-3.5 h-3.5" />Desde {auction.starting_price.toFixed(2)} &euro;</span>
                </div>
              </div>

              {/* Buy Now */}
              {hasBuyNow && !isOwner && (
                <div className="mb-4">
                  <Button onClick={handleBuyNow} disabled={buyingNow} className="w-full bg-[#ffb347] hover:bg-[#ffa01a] text-white rounded-full py-5 font-bold text-base shadow-md" data-testid="buy-now-btn">
                    {buyingNow ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <ShoppingCart className="w-5 h-5 mr-2" />}
                    Compralo ya por {auction.buy_now_price.toFixed(2)} &euro;
                  </Button>
                </div>
              )}
              {hasBuyNow && isOwner && (
                <div className="bg-[#ffb347]/10 rounded-xl p-3 mb-4 text-sm text-[#ffb347] font-medium">
                  Precio compra inmediata: {auction.buy_now_price.toFixed(2)} &euro;
                </div>
              )}

              {/* Bid section */}
              {isActive && !isOwner && (
                <div className="space-y-3">
                  <p className="text-sm text-slate-500">Tu puja (min. {minBid.toFixed(2)} &euro;)</p>
                  <div className="flex gap-2">
                    <Input type="number" min={minBid} step={0.5} value={bidAmount} onChange={(e) => setBidAmount(e.target.value)} className="rounded-xl" data-testid="detail-bid-input" />
                    <Button onClick={handleBid} disabled={bidding || parseFloat(bidAmount) < minBid} className="bg-[#18b29c] hover:bg-[#149682] text-white rounded-full px-6 font-bold" data-testid="detail-bid-btn">
                      {bidding ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Pujar'}
                    </Button>
                  </div>
                  {/* Auto-bid */}
                  <button onClick={() => setShowAutoBid(!showAutoBid)} className="text-sm text-[#18b29c] hover:underline flex items-center gap-1" data-testid="toggle-auto-bid">
                    <Zap className="w-3.5 h-3.5" /> Puja automatica
                  </button>
                  {showAutoBid && (
                    <div className="bg-[#f5f7fa] rounded-xl p-4 space-y-2">
                      <p className="text-sm text-slate-600">Establece un maximo y el sistema pujara automaticamente por ti hasta ese limite.</p>
                      <div className="flex gap-2">
                        <Input type="number" min={minBid} step={0.5} value={autoBidMax} onChange={(e) => setAutoBidMax(e.target.value)} placeholder={`Min. ${minBid.toFixed(2)}`} className="rounded-xl" data-testid="auto-bid-input" />
                        <Button onClick={handleAutoBid} disabled={settingAutoBid || !autoBidMax || parseFloat(autoBidMax) < minBid} className="bg-[#18b29c] text-white rounded-full" data-testid="auto-bid-btn">
                          {settingAutoBid ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Owner info */}
              {isOwner && isActive && (
                <div className="space-y-3">
                  <div className="bg-[#18b29c]/10 rounded-xl p-4 text-sm text-[#18b29c] font-medium" data-testid="own-auction-msg">Esta es tu subasta</div>
                  <Button onClick={handleCancel} disabled={cancelling} variant="destructive" className="w-full rounded-full" data-testid="cancel-auction-btn">
                    {cancelling ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <XCircle className="w-4 h-4 mr-1" />}
                    Cancelar subasta
                  </Button>
                </div>
              )}

              {/* Finished info */}
              {isFinished && (
                <div className="space-y-3">
                  <div className="bg-slate-100 rounded-xl p-4 text-sm text-slate-600" data-testid="auction-ended-msg">
                    {isWinner && <p className="font-bold text-[#18b29c] mb-1">Has ganado esta subasta! Contacta con el vendedor para coordinar el pago y la entrega.</p>}
                    {isOwner && auction.winner_name && <p className="font-bold text-[#18b29c] mb-1">Tu subasta ha terminado. El ganador es {auction.winner_name}.</p>}
                    {!isOwner && !isWinner && auction.winner_name && <p>Ganador: {auction.winner_name} con {auction.current_price.toFixed(2)} &euro;</p>}
                    {!auction.winner_name && <p>Esta subasta ha finalizado sin pujas.</p>}
                  </div>
                  {/* Contact button */}
                  {canContact && (
                    <div>
                      {!contactInfo ? (
                        <Button onClick={fetchContact} disabled={loadingContact} className="w-full bg-[#18b29c] text-white rounded-full" data-testid="contact-btn">
                          {loadingContact ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Mail className="w-4 h-4 mr-1" />}
                          Contactar
                        </Button>
                      ) : (
                        <div className="bg-[#18b29c]/10 rounded-xl p-4" data-testid="contact-info">
                          <p className="text-sm font-bold text-[#18b29c] mb-1">{contactInfo.role === 'seller' ? 'Datos del vendedor' : 'Datos del ganador'}</p>
                          <p className="text-sm text-slate-800">Nombre: {contactInfo.contact_name}</p>
                          <p className="text-sm text-slate-800">Email: <a href={`mailto:${contactInfo.contact_email}`} className="text-[#18b29c] underline">{contactInfo.contact_email}</a></p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {isCancelled && (
                <div className="bg-red-50 rounded-xl p-4 text-sm text-red-600" data-testid="cancelled-msg">
                  Esta subasta ha sido cancelada por el vendedor.
                </div>
              )}

              <Separator className="my-4" />
              <div className="space-y-3 text-sm">
                <div className="flex items-center gap-2 text-slate-600"><User className="w-4 h-4 text-slate-400" />Vendedor: <span className="font-medium">{auction.seller_name}</span></div>
                <div className="flex items-center gap-2 text-slate-600"><MapPin className="w-4 h-4 text-slate-400" />{auction.location}</div>
                <div className="flex items-center gap-2 text-slate-600"><Package className="w-4 h-4 text-slate-400" />{DELIVERY_LABELS[auction.delivery_type] || auction.delivery_type}</div>
              </div>
            </CardContent></Card>
          </div>
        </div>
      </div>
    </div>
  );
}
