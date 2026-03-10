import { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Camera, X, Loader2, CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent } from '@/components/ui/card';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';
import { toast } from 'sonner';

const CATEGORIES = ['Electr\u00F3nica', 'Hogar', 'Deporte', 'Moda', 'Motor', 'Libros', 'Juguetes', 'Otros'];
const LOCATIONS = {
  'Pen\u00EDnsula': ['Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'M\u00E1laga', 'Bilbao', 'Zaragoza', 'Alicante', 'Murcia', 'C\u00F3rdoba'],
  'Canarias': ['Tenerife', 'Gran Canaria', 'Lanzarote', 'Fuerteventura', 'La Palma', 'La Gomera', 'El Hierro'],
};
const DURATIONS = [
  { value: '1h', label: '1 hora' }, { value: '6h', label: '6 horas' }, { value: '12h', label: '12 horas' },
  { value: '24h', label: '24 horas' }, { value: '3d', label: '3 d\u00EDas' }, { value: '7d', label: '7 d\u00EDas' },
];

function compressImage(file) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const MAX = 800;
        let w = img.width, h = img.height;
        if (w > h) { if (w > MAX) { h = h * MAX / w; w = MAX; } }
        else { if (h > MAX) { w = w * MAX / h; h = MAX; } }
        canvas.width = w; canvas.height = h;
        canvas.getContext('2d').drawImage(img, 0, 0, w, h);
        resolve(canvas.toDataURL('image/jpeg', 0.7));
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  });
}

export default function CreateAuctionPage() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    title: '', description: '', category: '', location: '', delivery_type: 'both',
    images: [], starting_price: '', duration: '24h', buy_now_price: '',
  });

  useEffect(() => {
    if (!authLoading && !user) navigate('/auth?tab=login');
  }, [authLoading, user, navigate]);

  if (!user) return null;

  const handleImageUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (form.images.length + files.length > 6) { toast.error('Maximo 6 fotos'); return; }
    for (const file of files) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        const res = await api.post('/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
        setForm(prev => ({ ...prev, images: [...prev.images, res.data.url] }));
      } catch { toast.error('Error al subir imagen'); }
    }
    e.target.value = '';
  };

  const removeImage = (index) => setForm({ ...form, images: form.images.filter((_, i) => i !== index) });

  const handleSubmit = async () => {
    const price = parseFloat(form.starting_price);
    if (!price || price < 1) { toast.error('El precio minimo es 1 euro'); return; }
    const buyNow = form.buy_now_price ? parseFloat(form.buy_now_price) : null;
    if (buyNow !== null && buyNow <= price) { toast.error('El precio de compra inmediata debe ser mayor que el precio de salida'); return; }
    setLoading(true);
    try {
      const payload = { ...form, starting_price: price, buy_now_price: buyNow };
      const res = await api.post('/subastas', payload);
      toast.success('Subasta creada correctamente');
      navigate(`/subasta/${res.data.id}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al crear la subasta');
    } finally { setLoading(false); }
  };

  const canNextStep = () => {
    if (step === 1) return form.title && form.description && form.category && form.location;
    if (step === 2) return form.images.length >= 1;
    return form.starting_price !== '' && form.duration;
  };

  return (
    <div className="min-h-screen bg-[#f5f7fa] pb-20 md:pb-0">
      <div className="container mx-auto px-4 md:px-6 max-w-2xl py-8">
        <Link to="/" className="flex items-center gap-2 mb-6 text-slate-500 hover:text-[#18b29c] transition-colors" data-testid="create-back-link">
          <ArrowLeft className="w-4 h-4" /> Volver
        </Link>
        <h1 className="text-2xl md:text-3xl font-extrabold text-slate-800 mb-2" style={{ fontFamily: 'Nunito, sans-serif' }}>Publicar subasta</h1>

        <div className="flex items-center gap-2 mb-8" data-testid="create-progress">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2 flex-1">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-colors ${s === step ? 'bg-[#18b29c] text-white' : s < step ? 'bg-[#18b29c]/20 text-[#18b29c]' : 'bg-slate-200 text-slate-400'}`}>
                {s < step ? <CheckCircle className="w-4 h-4" /> : s}
              </div>
              {s < 3 && <div className={`flex-1 h-1 rounded ${s < step ? 'bg-[#18b29c]' : 'bg-slate-200'}`} />}
            </div>
          ))}
        </div>

        <Card className="border-0 shadow-lg rounded-2xl">
          <CardContent className="p-6">
            {step === 1 && (
              <div className="space-y-4" data-testid="create-step-1">
                <h2 className="font-bold text-lg text-slate-800 mb-4">Detalles del articulo</h2>
                <div><Label>Titulo</Label><Input placeholder="Ej: iPhone 13 como nuevo" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="rounded-xl mt-1" data-testid="create-title-input" /></div>
                <div><Label>Descripcion</Label><Textarea placeholder="Describe tu articulo con detalle..." value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="rounded-xl mt-1 min-h-[120px]" data-testid="create-description-input" /></div>
                <div><Label>Categoria</Label>
                  <Select value={form.category} onValueChange={(v) => setForm({ ...form, category: v })}>
                    <SelectTrigger className="rounded-xl mt-1" data-testid="create-category-select"><SelectValue placeholder="Selecciona categoria" /></SelectTrigger>
                    <SelectContent>{CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                  </Select></div>
                <div><Label>Ubicacion</Label>
                  <Select value={form.location} onValueChange={(v) => setForm({ ...form, location: v })}>
                    <SelectTrigger className="rounded-xl mt-1" data-testid="create-location-select"><SelectValue placeholder="Selecciona ubicacion" /></SelectTrigger>
                    <SelectContent>
                      <div className="px-2 py-1.5 text-xs font-bold text-slate-400 uppercase">Peninsula</div>
                      {LOCATIONS['Pen\u00EDnsula'].map((l) => <SelectItem key={l} value={l}>{l}</SelectItem>)}
                      <div className="px-2 py-1.5 text-xs font-bold text-[#ffb347] uppercase mt-2">Canarias</div>
                      {LOCATIONS['Canarias'].map((l) => <SelectItem key={l} value={l}>{l}</SelectItem>)}
                    </SelectContent>
                  </Select></div>
                <div><Label>Tipo de entrega</Label>
                  <Select value={form.delivery_type} onValueChange={(v) => setForm({ ...form, delivery_type: v })}>
                    <SelectTrigger className="rounded-xl mt-1" data-testid="create-delivery-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pickup">Recogida en mano</SelectItem>
                      <SelectItem value="shipping">Envio</SelectItem>
                      <SelectItem value="both">Ambos</SelectItem>
                    </SelectContent>
                  </Select></div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-4" data-testid="create-step-2">
                <h2 className="font-bold text-lg text-slate-800 mb-2">Fotos del articulo</h2>
                <p className="text-sm text-slate-500 mb-4">Sube entre 1 y 6 fotos. La primera sera la portada.</p>
                <div className="grid grid-cols-3 gap-3">
                  {form.images.map((img, i) => (
                    <div key={i} className="relative aspect-square rounded-xl overflow-hidden border-2 border-slate-200">
                      <img src={img} alt={`Foto ${i + 1}`} className="w-full h-full object-cover" />
                      <button onClick={() => removeImage(i)} className="absolute top-1 right-1 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center" data-testid={`remove-image-${i}`}><X className="w-3 h-3" /></button>
                      {i === 0 && <span className="absolute bottom-1 left-1 bg-[#18b29c] text-white text-[10px] font-bold px-2 py-0.5 rounded-full">Portada</span>}
                    </div>
                  ))}
                  {form.images.length < 6 && (
                    <label className="aspect-square rounded-xl border-2 border-dashed border-slate-300 flex flex-col items-center justify-center cursor-pointer hover:border-[#18b29c] hover:bg-[#18b29c]/5 transition-colors" data-testid="upload-image-btn">
                      <Camera className="w-8 h-8 text-slate-400 mb-1" /><span className="text-xs text-slate-400">Anadir foto</span>
                      <input type="file" accept="image/*" multiple className="hidden" onChange={handleImageUpload} />
                    </label>
                  )}
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-4" data-testid="create-step-3">
                <h2 className="font-bold text-lg text-slate-800 mb-4">Precio y duracion</h2>
                <div>
                  <Label>Precio de salida (euros)</Label>
                  <Input type="number" min={1} step={0.5} value={form.starting_price} onChange={(e) => setForm({ ...form, starting_price: e.target.value })} className="rounded-xl mt-1" placeholder="1.00" data-testid="create-price-input" />
                  <p className="text-xs text-slate-400 mt-1">Minimo 1 euro</p>
                </div>
                <div>
                  <Label>Precio de compra inmediata (euros) - Opcional</Label>
                  <Input type="number" min={0} step={0.5} value={form.buy_now_price} onChange={(e) => setForm({ ...form, buy_now_price: e.target.value })} className="rounded-xl mt-1" placeholder="Dejar vacio si no aplica" data-testid="create-buy-now-price-input" />
                  <p className="text-xs text-slate-400 mt-1">Si se rellena, debe ser mayor que el precio de salida. El comprador podra adquirirlo al instante.</p>
                </div>
                <div>
                  <Label>Duracion de la subasta</Label>
                  <Select value={form.duration} onValueChange={(v) => setForm({ ...form, duration: v })}>
                    <SelectTrigger className="rounded-xl mt-1" data-testid="create-duration-select"><SelectValue /></SelectTrigger>
                    <SelectContent>{DURATIONS.map((d) => <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="bg-[#f5f7fa] rounded-xl p-4 mt-4">
                  <h3 className="font-bold text-sm text-slate-600 mb-3">Resumen</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between"><span className="text-slate-500">Titulo</span><span className="font-medium text-slate-800 text-right max-w-[60%] truncate">{form.title}</span></div>
                    <div className="flex justify-between"><span className="text-slate-500">Categoria</span><span className="font-medium text-slate-800">{form.category}</span></div>
                    <div className="flex justify-between"><span className="text-slate-500">Ubicacion</span><span className="font-medium text-slate-800">{form.location}</span></div>
                    <div className="flex justify-between"><span className="text-slate-500">Fotos</span><span className="font-medium text-slate-800">{form.images.length}</span></div>
                    <div className="flex justify-between"><span className="text-slate-500">Precio inicio</span><span className="font-bold text-[#18b29c]">{form.starting_price ? parseFloat(form.starting_price).toFixed(2) : '0.00'} euros</span></div>
                    {form.buy_now_price && <div className="flex justify-between"><span className="text-slate-500">Compra inmediata</span><span className="font-bold text-[#ffb347]">{parseFloat(form.buy_now_price).toFixed(2)} euros</span></div>}
                    <div className="flex justify-between"><span className="text-slate-500">Duracion</span><span className="font-medium text-slate-800">{DURATIONS.find((d) => d.value === form.duration)?.label}</span></div>
                  </div>
                </div>
              </div>
            )}

            <div className="flex justify-between mt-8">
              {step > 1 ? <Button variant="outline" onClick={() => setStep(step - 1)} className="rounded-full" data-testid="create-prev-btn"><ArrowLeft className="w-4 h-4 mr-1" /> Anterior</Button> : <div />}
              {step < 3 ? (
                <Button onClick={() => setStep(step + 1)} disabled={!canNextStep()} className="bg-[#18b29c] hover:bg-[#149682] text-white rounded-full" data-testid="create-next-btn">Siguiente <ArrowRight className="w-4 h-4 ml-1" /></Button>
              ) : (
                <Button onClick={handleSubmit} disabled={loading || !canNextStep()} className="bg-[#18b29c] hover:bg-[#149682] text-white rounded-full" data-testid="create-submit-btn">
                  {loading && <Loader2 className="w-4 h-4 animate-spin mr-1" />} Publicar subasta
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
