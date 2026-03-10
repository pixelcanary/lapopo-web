import { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { ArrowLeft, Loader2 } from 'lucide-react';

export default function AuthPage() {
  const [searchParams] = useSearchParams();
  const defaultTab = searchParams.get('tab') || 'login';
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [registerForm, setRegisterForm] = useState({ name: '', email: '', password: '' });

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(loginForm.email, loginForm.password);
      toast.success('Bienvenido de nuevo');
      navigate('/');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al iniciar sesi\u00F3n');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await register(registerForm.name, registerForm.email, registerForm.password);
      toast.success('Cuenta creada correctamente');
      navigate('/');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al registrarse');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f5f7fa] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <Link
          to="/"
          className="flex items-center gap-2 mb-8 text-slate-500 hover:text-[#18b29c] transition-colors"
          data-testid="auth-back-link"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Volver</span>
        </Link>

        <div className="text-center mb-8">
          <h1
            className="text-3xl font-extrabold text-[#18b29c]"
            style={{ fontFamily: 'Nunito, sans-serif' }}
          >
            Lapopo
          </h1>
          <p className="text-slate-500 mt-2">Subastas de segunda mano desde 1&euro;</p>
        </div>

        <Card className="border-0 shadow-lg rounded-2xl">
          <Tabs defaultValue={defaultTab}>
            <CardHeader className="pb-0">
              <TabsList className="w-full grid grid-cols-2 rounded-xl" data-testid="auth-tabs">
                <TabsTrigger value="login" className="rounded-lg" data-testid="auth-login-tab">
                  Entrar
                </TabsTrigger>
                <TabsTrigger value="register" className="rounded-lg" data-testid="auth-register-tab">
                  Registrarse
                </TabsTrigger>
              </TabsList>
            </CardHeader>

            <CardContent className="pt-6">
              <TabsContent value="login">
                <form onSubmit={handleLogin} className="space-y-4" data-testid="login-form">
                  <div>
                    <Label htmlFor="login-email">Email</Label>
                    <Input
                      id="login-email"
                      type="email"
                      placeholder="tu@email.com"
                      value={loginForm.email}
                      onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
                      className="rounded-xl mt-1"
                      required
                      data-testid="login-email-input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="login-password">Contrase&ntilde;a</Label>
                    <Input
                      id="login-password"
                      type="password"
                      placeholder="&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;"
                      value={loginForm.password}
                      onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                      className="rounded-xl mt-1"
                      required
                      data-testid="login-password-input"
                    />
                  </div>
                  <Button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-[#18b29c] hover:bg-[#149682] text-white rounded-full py-6 font-bold text-base"
                    data-testid="login-submit-btn"
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Entrar'}
                  </Button>
                </form>
              </TabsContent>

              <TabsContent value="register">
                <form onSubmit={handleRegister} className="space-y-4" data-testid="register-form">
                  <div>
                    <Label htmlFor="reg-name">Nombre</Label>
                    <Input
                      id="reg-name"
                      type="text"
                      placeholder="Tu nombre"
                      value={registerForm.name}
                      onChange={(e) => setRegisterForm({ ...registerForm, name: e.target.value })}
                      className="rounded-xl mt-1"
                      required
                      data-testid="register-name-input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="reg-email">Email</Label>
                    <Input
                      id="reg-email"
                      type="email"
                      placeholder="tu@email.com"
                      value={registerForm.email}
                      onChange={(e) => setRegisterForm({ ...registerForm, email: e.target.value })}
                      className="rounded-xl mt-1"
                      required
                      data-testid="register-email-input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="reg-password">Contrase&ntilde;a</Label>
                    <Input
                      id="reg-password"
                      type="password"
                      placeholder="M&iacute;n. 6 caracteres"
                      value={registerForm.password}
                      onChange={(e) => setRegisterForm({ ...registerForm, password: e.target.value })}
                      className="rounded-xl mt-1"
                      required
                      minLength={6}
                      data-testid="register-password-input"
                    />
                  </div>
                  <Button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-[#18b29c] hover:bg-[#149682] text-white rounded-full py-6 font-bold text-base"
                    data-testid="register-submit-btn"
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Crear Cuenta'}
                  </Button>
                </form>
              </TabsContent>
            </CardContent>
          </Tabs>
        </Card>

        <p className="text-center text-sm text-slate-400 mt-6">
          Demo: carlos@lapopo.es / demo123
        </p>
      </div>
    </div>
  );
}
