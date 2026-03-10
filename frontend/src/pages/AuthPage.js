import { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { ArrowLeft, Loader2, Mail } from 'lucide-react';
import api from '@/lib/api';

export default function AuthPage() {
  const [searchParams] = useSearchParams();
  const defaultTab = searchParams.get('tab') || 'login';
  const resetToken = searchParams.get('token') || '';
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [registerForm, setRegisterForm] = useState({ name: '', email: '', password: '' });
  const [showForgot, setShowForgot] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotSent, setForgotSent] = useState(false);
  const [showReset, setShowReset] = useState(!!resetToken);
  const [resetPwd, setResetPwd] = useState('');
  const [resetPwdConfirm, setResetPwdConfirm] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try { await login(loginForm.email, loginForm.password); toast.success('Bienvenido de nuevo'); navigate('/'); }
    catch (err) { toast.error(err.response?.data?.detail || 'Error al iniciar sesion'); }
    finally { setLoading(false); }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    try { await register(registerForm.name, registerForm.email, registerForm.password); toast.success('Cuenta creada correctamente'); navigate('/'); }
    catch (err) { toast.error(err.response?.data?.detail || 'Error al registrarse'); }
    finally { setLoading(false); }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    try { await api.post('/auth/recuperar-password', { email: forgotEmail }); setForgotSent(true); }
    catch { toast.error('Error al enviar'); }
    finally { setLoading(false); }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (resetPwd.length < 8) { toast.error('Minimo 8 caracteres'); return; }
    if (resetPwd !== resetPwdConfirm) { toast.error('Las contrasenas no coinciden'); return; }
    setLoading(true);
    try {
      await api.post('/auth/resetear-password', { token: resetToken, new_password: resetPwd });
      toast.success('Contrasena restablecida. Ya puedes iniciar sesion.');
      setShowReset(false);
    } catch (err) { toast.error(err.response?.data?.detail || 'Enlace invalido o expirado'); }
    finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-[#f5f7fa] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <Link to="/" className="flex items-center gap-2 mb-8 text-slate-500 hover:text-[#18b29c] transition-colors" data-testid="auth-back-link">
          <ArrowLeft className="w-4 h-4" /><span>Volver</span>
        </Link>
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold text-[#18b29c]" style={{ fontFamily: 'Nunito, sans-serif' }}>Lapopo</h1>
          <p className="text-slate-500 mt-2">Subastas de segunda mano desde 1&euro;</p>
        </div>

        {showReset ? (
          <Card className="border-0 shadow-lg rounded-2xl">
            <CardContent className="p-6">
              <h2 className="font-bold text-lg text-slate-800 mb-4">Restablecer contrasena</h2>
              <form onSubmit={handleResetPassword} className="space-y-4" data-testid="reset-password-form">
                <div>
                  <Label>Nueva contrasena</Label>
                  <Input type="password" placeholder="Min. 8 caracteres" value={resetPwd} onChange={(e) => setResetPwd(e.target.value)} className="rounded-xl mt-1" required data-testid="reset-pwd-input" />
                </div>
                <div>
                  <Label>Confirmar contrasena</Label>
                  <Input type="password" placeholder="Repite la contrasena" value={resetPwdConfirm} onChange={(e) => setResetPwdConfirm(e.target.value)} className="rounded-xl mt-1" required data-testid="reset-pwd-confirm-input" />
                </div>
                <Button type="submit" disabled={loading} className="w-full bg-[#18b29c] text-white rounded-full py-6 font-bold" data-testid="reset-pwd-submit">
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Restablecer contrasena'}
                </Button>
              </form>
            </CardContent>
          </Card>
        ) : showForgot ? (
          <Card className="border-0 shadow-lg rounded-2xl">
            <CardContent className="p-6">
              <h2 className="font-bold text-lg text-slate-800 mb-4">Recuperar contrasena</h2>
              {forgotSent ? (
                <div className="text-center py-4" data-testid="forgot-sent-msg">
                  <Mail className="w-10 h-10 text-[#18b29c] mx-auto mb-3" />
                  <p className="text-sm text-slate-600">Si ese email esta registrado, recibiras un enlace de recuperacion.</p>
                  <Button variant="outline" onClick={() => { setShowForgot(false); setForgotSent(false); }} className="rounded-full mt-4">Volver al login</Button>
                </div>
              ) : (
                <form onSubmit={handleForgotPassword} className="space-y-4" data-testid="forgot-password-form">
                  <div>
                    <Label>Email</Label>
                    <Input type="email" placeholder="tu@email.com" value={forgotEmail} onChange={(e) => setForgotEmail(e.target.value)} className="rounded-xl mt-1" required data-testid="forgot-email-input" />
                  </div>
                  <Button type="submit" disabled={loading} className="w-full bg-[#18b29c] text-white rounded-full py-6 font-bold" data-testid="forgot-submit">
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Enviar enlace'}
                  </Button>
                  <button type="button" onClick={() => setShowForgot(false)} className="text-sm text-slate-500 hover:text-[#18b29c] w-full text-center">Volver al login</button>
                </form>
              )}
            </CardContent>
          </Card>
        ) : (
          <Card className="border-0 shadow-lg rounded-2xl">
            <Tabs defaultValue={defaultTab}>
              <CardHeader className="pb-0">
                <TabsList className="w-full grid grid-cols-2 rounded-xl" data-testid="auth-tabs">
                  <TabsTrigger value="login" className="rounded-lg" data-testid="auth-login-tab">Entrar</TabsTrigger>
                  <TabsTrigger value="register" className="rounded-lg" data-testid="auth-register-tab">Registrarse</TabsTrigger>
                </TabsList>
              </CardHeader>
              <CardContent className="pt-6">
                <TabsContent value="login">
                  <form onSubmit={handleLogin} className="space-y-4" data-testid="login-form">
                    <div>
                      <Label htmlFor="login-email">Email</Label>
                      <Input id="login-email" type="email" placeholder="tu@email.com" value={loginForm.email} onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })} className="rounded-xl mt-1" required data-testid="login-email-input" />
                    </div>
                    <div>
                      <Label htmlFor="login-password">Contrasena</Label>
                      <Input id="login-password" type="password" placeholder="********" value={loginForm.password} onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })} className="rounded-xl mt-1" required data-testid="login-password-input" />
                    </div>
                    <Button type="submit" disabled={loading} className="w-full bg-[#18b29c] hover:bg-[#149682] text-white rounded-full py-6 font-bold text-base" data-testid="login-submit-btn">
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Entrar'}
                    </Button>
                    <button type="button" onClick={() => setShowForgot(true)} className="text-sm text-slate-500 hover:text-[#18b29c] w-full text-center" data-testid="forgot-password-link">
                      Olvidaste tu contrasena?
                    </button>
                  </form>
                </TabsContent>
                <TabsContent value="register">
                  <form onSubmit={handleRegister} className="space-y-4" data-testid="register-form">
                    <div>
                      <Label htmlFor="reg-name">Nombre</Label>
                      <Input id="reg-name" type="text" placeholder="Tu nombre" value={registerForm.name} onChange={(e) => setRegisterForm({ ...registerForm, name: e.target.value })} className="rounded-xl mt-1" required data-testid="register-name-input" />
                    </div>
                    <div>
                      <Label htmlFor="reg-email">Email</Label>
                      <Input id="reg-email" type="email" placeholder="tu@email.com" value={registerForm.email} onChange={(e) => setRegisterForm({ ...registerForm, email: e.target.value })} className="rounded-xl mt-1" required data-testid="register-email-input" />
                    </div>
                    <div>
                      <Label htmlFor="reg-password">Contrasena</Label>
                      <Input id="reg-password" type="password" placeholder="Min. 6 caracteres" value={registerForm.password} onChange={(e) => setRegisterForm({ ...registerForm, password: e.target.value })} className="rounded-xl mt-1" required minLength={6} data-testid="register-password-input" />
                    </div>
                    <Button type="submit" disabled={loading} className="w-full bg-[#18b29c] hover:bg-[#149682] text-white rounded-full py-6 font-bold text-base" data-testid="register-submit-btn">
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Crear Cuenta'}
                    </Button>
                  </form>
                </TabsContent>
              </CardContent>
            </Tabs>
          </Card>
        )}

        <p className="text-center text-sm text-slate-400 mt-6">Demo: carlos@lapopo.es / demo123</p>
      </div>
    </div>
  );
}
