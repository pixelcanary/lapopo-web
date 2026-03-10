import { Link } from 'react-router-dom';
import { MapPin, Gavel, Hand } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Countdown } from './Countdown';
import { isCanarias } from '@/lib/api';

export function AuctionCard({ auction }) {
  const canarias = isCanarias(auction.location);

  return (
    <Link
      to={`/subasta/${auction.id}`}
      data-testid={`auction-card-${auction.id}`}
      className="bg-white rounded-2xl shadow-sm hover:shadow-md transition-all duration-300 border border-slate-100 overflow-hidden group relative block"
    >
      <div className="relative aspect-square overflow-hidden">
        <img
          src={auction.images?.[0] || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&q=80&w=400'}
          alt={auction.title}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
        />
        {canarias && (
          <div className="absolute top-2 left-2">
            <Badge className="bg-[#ffb347]/90 text-white border-0 text-xs font-bold gap-1" data-testid="canarias-badge">
              <Hand className="w-3 h-3" />
              Canarias
            </Badge>
          </div>
        )}
        <div className="absolute top-2 right-2 bg-white/90 backdrop-blur-sm rounded-full px-2.5 py-1 shadow-sm">
          <Countdown endTime={auction.end_time} compact />
        </div>
      </div>

      <div className="p-4">
        <h3 className="font-bold text-slate-800 line-clamp-2 mb-2 group-hover:text-[#18b29c] transition-colors text-sm leading-snug">
          {auction.title}
        </h3>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-2xl font-extrabold text-[#18b29c]" style={{ fontFamily: 'Nunito, sans-serif' }}>
              {auction.current_price.toFixed(2)} &euro;
            </p>
            {auction.starting_price < auction.current_price && (
              <p className="text-xs text-slate-400 line-through">{auction.starting_price.toFixed(2)} &euro;</p>
            )}
          </div>
          <div className="flex items-center gap-1 text-slate-500 text-sm">
            <Gavel className="w-3.5 h-3.5" />
            <span>{auction.bid_count}</span>
          </div>
        </div>
        <div className="flex items-center gap-1 mt-2 text-xs text-slate-500">
          <MapPin className="w-3 h-3" />
          {auction.location}
        </div>
      </div>
    </Link>
  );
}
