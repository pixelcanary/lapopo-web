import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Check, Crown, Zap, ShoppingCart, Loader2, ArrowLeft, Star, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function PricingPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [plans, setPlans] = useState(null);
  const [myPlan, setMyPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(null);
  const [polling, setPolling] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const res = await api.get('/planes');
      setPlans(res.data);
      if (user) {
        const planRes = await api.get('/suscripciones/mi-plan');
        setMyPlan(planRes.data);
      }
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [user]);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    const sessionId = searchParams.get('session_id');
    if (sessionId && user) {
      setPolling(true);
      pollPayment(sessionId, 0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, user]);

  const pollPayment = async (sessionId, attempt) => {
    if (attempt >= 6) { setPolling(false); toast.error('No se pudo verificar el pago'); return; }
    try {
      const res = await api.get(`/pagos/estado/${sessionId}`);
      if (res.data.payment_status === 'paid') {
        setPolling(false);
        toast.success('Pago completado. Tu plan se ha actualizado.');
        fetchData();
        return;
      }
    } catch { /* ignore */ }
    setTimeout(() => pollPayment(sessionId, attempt + 1), 2500);
  };

  const subscribe = async (plan) => {
    if (!user) { navigate('/auth?tab=login'); return; }
    setPurchasing(plan);
    try {
      const res = await api.post('/suscripciones/crear-sesion', { plan, origin_url: window.location.origin });
      window.location.href = res.data.url;
    } catch (err) { toast.error(err.response?.data?.detail || 'Error'); setPurchasing(null); }
  };

  const cancelPlan = async () => {
    if (!window.confirm('Volver al plan Gratis?')) return;
    try {
      await api.post('/suscripciones/cancelar');
      toast.success('Plan cancelado');
      fetchData();
    } catch { toast.error('Error'); }
  };

  if (loading) return <div className="min-h-screen bg-[#f5f7fa] flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-[#18b29c]" /></div>;

  const planList = plans?.plans || {};
  const currentPlan = myPlan?.plan || 'free';

  const planConfig = [
    { key: 'free', icon: ShoppingCart, color: '#94a3b8', gradient: 'from-slate-50 to-white', features: ['Hasta 5 subastas/mes', 'Pujas ilimitadas', 'Favoritos y mensajeria'] },
    { key: 'vendedor', icon: Zap, color: '#18b29c', gradient: 'from-[#18b29c]/5 to-white', popular: true, features: ['Subastas ilimitadas', '1 subasta destacada gratis/mes', 'Todas las funciones del plan Gratis'] },
    { key: 'pro', icon: Crown, color: '#ffb347', gradient: 'from-[#ffb347]/5 to-white', features: ['Subastas ilimitadas', '3 subastas destacadas gratis/mes', 'Badge "Vendedor verificado"', 'Prioridad en busquedas'] },
  ];

  return (
    <div className="min-h-screen bg-[#f5f7fa] pb-20 md:pb-0" data-testid="pricing-page">
      <div className="container mx-auto px-4 md:px-6 max-w-5xl py-8">
        <button onClick={() => navigate('/')} className="flex items-center gap-2 text-slate-400 hover:text-[#18b29c] mb-6 transition-colors" data-testid="pricing-back">
          <ArrowLeft className="w-4 h-4" /> Volver
        </button>

        {polling && (
          <div className="bg-[#18b29c]/10 border border-[#18b29c]/20 rounded-xl p-4 mb-6 flex items-center gap-3" data-testid="payment-polling">
            <Loader2 className="w-5 h-5 animate-spin text-[#18b29c]" />
            <span className="text-sm text-[#18b29c] font-medium">Verificando tu pago...</span>
          </div>
        )}

        <div className="text-center mb-10">
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-800 mb-3" style={{ fontFamily: 'Nunito, sans-serif' }} data-testid="pricing-title">
            Planes y Precios
          </h1>
          <p className="text-slate-500 max-w-lg mx-auto">Elige el plan que mejor se adapte a tus necesidades de venta</p>
          {!plans?.payments_enabled && (
            <Badge className="mt-3 bg-[#18b29c]/10 text-[#18b29c] border-0 rounded-full" data-testid="payments-off-badge">
              <Shield className="w-3 h-3 mr-1" /> Sistema de pagos desactivado - Todo es gratis
            </Badge>
          )}
        </div>

        <div className="grid md:grid-cols-3 gap-6 mb-12">
          {planConfig.map(({ key, icon: Icon, color, gradient, popular, features }) => {
            const plan = planList[key];
            if (!plan) return null;
            const isCurrent = currentPlan === key;
            return (
              <Card key={key} className={`relative border-0 shadow-sm rounded-2xl overflow-hidden transition-all hover:shadow-lg ${popular ? 'ring-2 ring-[#18b29c] scale-[1.02]' : ''}`} data-testid={`plan-card-${key}`}>
                {popular && (
                  <div className="absolute top-0 right-0 bg-[#18b29c] text-white text-xs font-bold px-3 py-1 rounded-bl-xl">Popular</div>
                )}
                <CardContent className={`p-6 bg-gradient-to-b ${gradient}`}>
                  <div className="flex items-center gap-2 mb-3">
                    <Icon className="w-6 h-6" style={{ color }} />
                    <h2 className="text-xl font-extrabold text-slate-800" style={{ fontFamily: 'Nunito, sans-serif' }}>{plan.name}</h2>
                  </div>
                  <div className="mb-4">
                    <span className="text-4xl font-extrabold text-slate-800" style={{ fontFamily: 'Nunito, sans-serif' }}>
                      {plan.price > 0 ? `${plan.price.toFixed(2)}\u20AC` : 'Gratis'}
                    </span>
                    {plan.price > 0 && <span className="text-slate-500 text-sm">/mes</span>}
                  </div>
                  <ul className="space-y-2 mb-6">
                    {features.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                        <Check className="w-4 h-4 mt-0.5 flex-shrink-0" style={{ color }} />
                        {f}
                      </li>
                    ))}
                  </ul>
                  {isCurrent ? (
                    <div className="space-y-2">
                      <Button disabled className="w-full rounded-full bg-slate-100 text-slate-500" data-testid={`plan-current-${key}`}>
                        Tu plan actual
                      </Button>
                      {key !== 'free' && (
                        <Button variant="ghost" onClick={cancelPlan} className="w-full rounded-full text-xs text-slate-400" data-testid="cancel-plan-btn">
                          Volver a Gratis
                        </Button>
                      )}
                    </div>
                  ) : plan.price > 0 ? (
                    <Button
                      onClick={() => subscribe(key)}
                      disabled={purchasing === key || !plans?.payments_enabled}
                      className="w-full rounded-full text-white"
                      style={{ backgroundColor: color }}
                      data-testid={`plan-subscribe-${key}`}
                    >
                      {purchasing === key ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : null}
                      {plans?.payments_enabled ? 'Suscribirse' : 'Pagos desactivados'}
                    </Button>
                  ) : (
                    <Button disabled className="w-full rounded-full bg-slate-100 text-slate-500">
                      Plan por defecto
                    </Button>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Featured options */}
        <div className="mb-8">
          <h2 className="text-2xl font-extrabold text-slate-800 mb-4 text-center" style={{ fontFamily: 'Nunito, sans-serif' }}>
            Destaca tus subastas
          </h2>
          <div className="grid sm:grid-cols-3 gap-4">
            {[
              { key: 'destacada', icon: Star, color: '#d4a017', badge: 'Destacada', desc: 'Badge dorado y prioridad en su seccion' },
              { key: 'home', icon: ShoppingCart, color: '#18b29c', badge: 'Home', desc: 'Aparece en Subastas Destacadas de la portada' },
              { key: 'urgente', icon: Zap, color: '#f97316', badge: 'Urgente', desc: 'Badge naranja con prioridad visual' },
            ].map(({ key, icon: Icon, color, badge, desc }) => {
              const opt = plans?.featured_options?.[key];
              return (
                <Card key={key} className="border-0 shadow-sm rounded-xl" data-testid={`featured-option-${key}`}>
                  <CardContent className="p-4 text-center">
                    <Icon className="w-6 h-6 mx-auto mb-2" style={{ color }} />
                    <Badge className="text-white text-xs mb-2" style={{ backgroundColor: color }}>{badge}</Badge>
                    <p className="text-xs text-slate-500 mb-2">{desc}</p>
                    <p className="text-lg font-bold text-slate-800">{opt?.price?.toFixed(2)}&euro;/subasta</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
