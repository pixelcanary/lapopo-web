import { useState, useEffect } from 'react';
import { Clock } from 'lucide-react';

export function Countdown({ endTime, compact = false }) {
  const [timeLeft, setTimeLeft] = useState('');
  const [isUrgent, setIsUrgent] = useState(false);
  const [isEnded, setIsEnded] = useState(false);

  useEffect(() => {
    const calc = () => {
      const now = new Date();
      const end = new Date(endTime);
      const diff = end - now;
      if (diff <= 0) {
        setTimeLeft('Finalizada');
        setIsEnded(true);
        return;
      }
      const days = Math.floor(diff / 86400000);
      const hours = Math.floor((diff % 86400000) / 3600000);
      const minutes = Math.floor((diff % 3600000) / 60000);
      const seconds = Math.floor((diff % 60000) / 1000);
      setIsUrgent(diff < 86400000);
      if (compact) {
        if (days > 0) setTimeLeft(`${days}d ${hours}h`);
        else if (hours > 0) setTimeLeft(`${hours}h ${minutes}m`);
        else setTimeLeft(`${minutes}m ${seconds}s`);
      } else {
        if (days > 0) setTimeLeft(`${days}d ${hours}h ${minutes}m`);
        else if (hours > 0) setTimeLeft(`${hours}h ${minutes}m ${seconds}s`);
        else setTimeLeft(`${minutes}m ${seconds}s`);
      }
    };
    calc();
    const interval = setInterval(calc, 1000);
    return () => clearInterval(interval);
  }, [endTime, compact]);

  if (isEnded) {
    return <span className="text-slate-400 font-medium text-sm" data-testid="countdown-ended">Finalizada</span>;
  }

  return (
    <span
      className={`flex items-center gap-1 font-semibold text-sm ${isUrgent ? 'text-red-500' : 'text-slate-600'}`}
      data-testid="countdown-timer"
    >
      <Clock className="w-3.5 h-3.5" />
      {timeLeft}
    </span>
  );
}
