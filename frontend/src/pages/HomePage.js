import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Search, Clock, Tag, MapPin, Laptop, Home as HomeIcon, Camera, Truck, ChevronRight, HelpCircle, Star } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { AuctionCard } from '@/components/AuctionCard';
import api from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

const QUICK_FILTERS = [
  { id: 'ending_soon', label: 'Terminan pronto', icon: Clock },
  { id: 'from_1', label: 'Desde 1\u20AC', icon: Tag },
  { id: 'canarias', label: 'Solo Canarias', icon: MapPin },
  { id: 'electronica', label: 'Electr\u00F3nica', icon: Laptop },
  { id: 'hogar', label: 'Hogar', icon: HomeIcon },
];

const FAQ_ITEMS = [
  { q: '\u00BFC\u00F3mo funciona una subasta en Lapopo?', a: 'Publica tu art\u00EDculo con un precio de salida desde 1\u20AC, elige la duraci\u00F3n y los compradores pujan. Cuando termina el tiempo, el que m\u00E1s puj\u00F3 se lo lleva.' },
  { q: '\u00BFCu\u00E1nto cuesta publicar?', a: 'Publicar en Lapopo es completamente gratuito. No cobramos comisiones por ahora.' },
  { q: '\u00BFQu\u00E9 es "Solo Canarias"?', a: 'Es una secci\u00F3n dedicada a art\u00EDculos en las Islas Canarias, con opci\u00F3n de recogida en mano para evitar gastos de env\u00EDo.' },
  { q: '\u00BFC\u00F3mo pujo?', a: 'Entra en la subasta que te interese y pulsa "Pujar". Introduce una cantidad mayor al precio actual (m\u00EDnimo +0,50\u20AC).' },
  { q: '\u00BFQu\u00E9 pasa cuando gano una subasta?', a: 'El vendedor se pondr\u00E1 en contacto contigo para coordinar el pago y la entrega.' },
];

export default function HomePage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [auctions, setAuctions] = useState([]);
  const [canariasAuctions, setCanariasAuctions] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (searchParams.get('canarias') === 'true') {
      setActiveFilter('canarias');
    }
  }, [searchParams]);

  const fetchAuctions = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (activeFilter === 'ending_soon') params.sort = 'ending_soon';
      if (activeFilter === 'from_1') params.sort = 'price_low';
      if (activeFilter === 'canarias') params.canarias = true;
      if (activeFilter === 'electronica') params.category = 'Electr\u00F3nica';
      if (activeFilter === 'hogar') params.category = 'Hogar';
      if (searchQuery) params.search = searchQuery;
      const res = await api.get('/subastas', { params });
      setAuctions(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [activeFilter, searchQuery]);

  const fetchCanariasAuctions = useCallback(async () => {
    try {
      const res = await api.get('/subastas', { params: { canarias: true } });
      setCanariasAuctions(res.data.slice(0, 4));
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    fetchAuctions();
    fetchCanariasAuctions();
  }, [fetchAuctions, fetchCanariasAuctions]);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchAuctions();
  };

  return (
    <div className="min-h-screen bg-[#f5f7fa] pb-20 md:pb-0">
      {/* Hero */}
      <section className="relative overflow-hidden" style={{ background: 'linear-gradient(135deg, #18b29c 0%, #1cd1b6 100%)' }}>
        <div className="absolute inset-0 opacity-[0.07]" style={{ backgroundImage: 'radial-gradient(circle at 25% 25%, white 1px, transparent 1px)', backgroundSize: '32px 32px' }} />
        <div className="container mx-auto px-4 md:px-6 max-w-7xl py-16 md:py-24 relative">
          <div className="max-w-2xl">
            <h1
              className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white leading-tight"
              style={{ fontFamily: 'Nunito, sans-serif' }}
              data-testid="hero-title"
            >
              Compra y vende en subastas desde <span className="text-[#ffb347]">1&euro;</span>
            </h1>
            <p className="text-white/80 text-lg mt-4 mb-8">
              La plataforma de subastas de segunda mano para Espa&ntilde;a y Canarias
            </p>
            <form onSubmit={handleSearch} className="flex gap-2 max-w-lg">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <Input
                  placeholder="Buscar subastas..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 rounded-xl h-12 bg-white border-0 shadow-lg text-slate-800"
                  data-testid="hero-search-input"
                />
              </div>
              <Button
                type="submit"
                className="bg-[#ffb347] hover:bg-[#ffa01a] text-white rounded-xl h-12 px-6 font-bold shadow-lg"
                data-testid="hero-search-btn"
              >
                Buscar
              </Button>
            </form>
          </div>
        </div>
      </section>

      {/* Quick Filters */}
      <section className="container mx-auto px-4 md:px-6 max-w-7xl -mt-6 relative z-10">
        <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
          {QUICK_FILTERS.map((filter) => (
            <button
              key={filter.id}
              onClick={() => setActiveFilter(activeFilter === filter.id ? null : filter.id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-full whitespace-nowrap font-medium text-sm transition-all shadow-sm ${
                activeFilter === filter.id
                  ? 'bg-[#18b29c] text-white shadow-md'
                  : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'
              }`}
              data-testid={`filter-${filter.id}`}
            >
              <filter.icon className="w-4 h-4" />
              {filter.label}
            </button>
          ))}
        </div>
      </section>

      {/* Featured Auctions (home type) */}
      {!loading && !activeFilter && auctions.filter(a => a.featured?.includes('home')).length > 0 && (
        <section className="container mx-auto px-4 md:px-6 max-w-7xl pt-10 pb-2" data-testid="featured-home-section">
          <h2 className="text-2xl md:text-3xl font-bold text-slate-800 mb-4" style={{ fontFamily: 'Nunito, sans-serif' }}>
            <Star className="w-6 h-6 inline text-[#d4a017] mr-1 fill-[#d4a017]" />
            Subastas Destacadas
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 md:gap-6">
            {auctions.filter(a => a.featured?.includes('home')).map(a => <AuctionCard key={a.id} auction={a} />)}
          </div>
        </section>
      )}

      {/* Auctions Grid */}
      <section className="container mx-auto px-4 md:px-6 max-w-7xl py-12">
        <div className="flex items-center justify-between mb-6">
          <h2
            className="text-2xl md:text-3xl font-bold text-slate-800"
            style={{ fontFamily: 'Nunito, sans-serif' }}
            data-testid="section-title"
          >
            {activeFilter === 'canarias'
              ? 'Solo Canarias'
              : activeFilter
              ? QUICK_FILTERS.find((f) => f.id === activeFilter)?.label
              : 'Subastas Destacadas'}
          </h2>
          <span className="text-sm text-slate-500">{auctions.length} subastas</span>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 md:gap-6">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="bg-white rounded-2xl overflow-hidden animate-pulse">
                <div className="aspect-square bg-slate-200" />
                <div className="p-4 space-y-3">
                  <div className="h-4 bg-slate-200 rounded w-3/4" />
                  <div className="h-6 bg-slate-200 rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : auctions.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 md:gap-6" data-testid="auctions-grid">
            {auctions.map((auction) => (
              <AuctionCard key={auction.id} auction={auction} />
            ))}
          </div>
        ) : (
          <div className="text-center py-16" data-testid="empty-state">
            <Search className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500 text-lg">No se encontraron subastas</p>
            <Button
              onClick={() => { setActiveFilter(null); setSearchQuery(''); }}
              className="mt-4 rounded-full"
              variant="outline"
              data-testid="clear-filters-btn"
            >
              Limpiar filtros
            </Button>
          </div>
        )}
      </section>

      {/* Solo Canarias Section */}
      {!activeFilter && canariasAuctions.length > 0 && (
        <section className="py-12 md:py-16" style={{ background: 'linear-gradient(90deg, rgba(255,179,71,0.08) 0%, rgba(255,179,71,0.03) 100%)' }} data-testid="canarias-section">
          <div className="container mx-auto px-4 md:px-6 max-w-7xl">
            <div className="flex items-center justify-between mb-6">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Badge className="bg-[#ffb347] text-white border-0 font-bold rounded-full">Solo Canarias</Badge>
                  <Badge variant="outline" className="border-[#ffb347]/30 text-[#ffb347] font-medium rounded-full">Recogida en mano</Badge>
                </div>
                <h2 className="text-2xl md:text-3xl font-bold text-slate-800" style={{ fontFamily: 'Nunito, sans-serif' }}>
                  Subastas en las Islas
                </h2>
              </div>
              <Button
                variant="ghost"
                onClick={() => setActiveFilter('canarias')}
                className="text-[#ffb347] hover:text-[#ffa01a] font-medium"
                data-testid="canarias-see-all-btn"
              >
                Ver todas <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
              {canariasAuctions.map((auction) => (
                <AuctionCard key={auction.id} auction={auction} />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Sell in 3 Steps */}
      {!activeFilter && (
        <section className="container mx-auto px-4 md:px-6 max-w-7xl py-12 md:py-20" data-testid="sell-steps-section">
          <h2
            className="text-2xl md:text-3xl font-bold text-center text-slate-800 mb-12"
            style={{ fontFamily: 'Nunito, sans-serif' }}
          >
            Vende en 3 pasos
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8">
            {[
              { icon: Camera, title: 'Sube tus fotos', desc: 'Haz fotos claras de tu art\u00EDculo. Cuantas m\u00E1s, mejor.', step: '1' },
              { icon: Tag, title: 'Pon el precio', desc: 'Empieza desde 1\u20AC y elige la duraci\u00F3n de la subasta.', step: '2' },
              { icon: Truck, title: 'Vende y env\u00EDa', desc: 'El ganador paga y t\u00FA env\u00EDas o qued\u00E1is en persona.', step: '3' },
            ].map((item) => (
              <div
                key={item.step}
                className="bg-white rounded-3xl p-8 shadow-sm border border-slate-100 flex flex-col items-center text-center group hover:shadow-md transition-all duration-300"
              >
                <div className="w-16 h-16 rounded-2xl bg-[#18b29c]/10 flex items-center justify-center mb-4 group-hover:bg-[#18b29c]/20 transition-colors">
                  <item.icon className="w-8 h-8 text-[#18b29c]" />
                </div>
                <span className="text-xs font-bold text-[#18b29c] uppercase tracking-wider mb-2">
                  Paso {item.step}
                </span>
                <h3 className="text-lg font-bold text-slate-800 mb-2">{item.title}</h3>
                <p className="text-slate-500 text-sm">{item.desc}</p>
              </div>
            ))}
          </div>
          <div className="text-center mt-10">
            <Button
              onClick={() => navigate(user ? '/vender' : '/auth?tab=register')}
              className="bg-[#18b29c] hover:bg-[#149682] text-white rounded-full px-8 py-6 text-lg font-bold shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all active:scale-95"
              data-testid="sell-cta-btn"
            >
              Empezar a vender
            </Button>
          </div>
        </section>
      )}

      {/* FAQ */}
      {!activeFilter && (
        <section id="ayuda" className="bg-white py-12 md:py-20" data-testid="faq-section">
          <div className="container mx-auto px-4 md:px-6 max-w-3xl">
            <div className="flex items-center gap-3 justify-center mb-8">
              <HelpCircle className="w-6 h-6 text-[#18b29c]" />
              <h2
                className="text-2xl md:text-3xl font-bold text-slate-800"
                style={{ fontFamily: 'Nunito, sans-serif' }}
              >
                Preguntas Frecuentes
              </h2>
            </div>
            <Accordion type="single" collapsible className="space-y-3">
              {FAQ_ITEMS.map((item, i) => (
                <AccordionItem key={i} value={`faq-${i}`} className="border rounded-xl px-4 bg-slate-50/50">
                  <AccordionTrigger
                    className="text-left font-semibold text-slate-700 hover:text-[#18b29c] hover:no-underline"
                    data-testid={`faq-trigger-${i}`}
                  >
                    {item.q}
                  </AccordionTrigger>
                  <AccordionContent className="text-slate-500 leading-relaxed">
                    {item.a}
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-400 py-8" data-testid="footer">
        <div className="container mx-auto px-4 md:px-6 max-w-7xl">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xl font-extrabold text-[#18b29c]" style={{ fontFamily: 'Nunito, sans-serif' }}>Lapopo</span>
              <span className="text-sm">&copy; 2026</span>
            </div>
            <div className="flex gap-6 text-sm">
              <a href="/precios" className="hover:text-white transition-colors" data-testid="footer-pricing">Precios</a>
              <a href="#" className="hover:text-white transition-colors" data-testid="footer-terms">T&eacute;rminos y condiciones</a>
              <a href="#" className="hover:text-white transition-colors" data-testid="footer-privacy">Privacidad</a>
              <a href="#" className="hover:text-white transition-colors" data-testid="footer-contact">Contacto</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
