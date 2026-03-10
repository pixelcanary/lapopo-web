import { Star } from 'lucide-react';

export function StarRating({ rating = 0, count = 0, size = 'sm', interactive = false, onRate = null, showCount = true }) {
  const stars = [1, 2, 3, 4, 5];
  const sizeClasses = { xs: 'w-3 h-3', sm: 'w-4 h-4', md: 'w-5 h-5', lg: 'w-6 h-6' };
  const iconSize = sizeClasses[size] || sizeClasses.sm;

  return (
    <div className="flex items-center gap-1">
      <div className="flex">
        {stars.map((s) => (
          <button
            key={s}
            type="button"
            disabled={!interactive}
            onClick={() => interactive && onRate?.(s)}
            className={`${interactive ? 'cursor-pointer hover:scale-110' : 'cursor-default'} transition-transform`}
            data-testid={`star-${s}`}
          >
            <Star
              className={`${iconSize} ${s <= Math.round(rating) ? 'text-[#ffb347] fill-[#ffb347]' : 'text-slate-300'}`}
            />
          </button>
        ))}
      </div>
      {showCount && count > 0 && (
        <span className={`text-slate-500 ${size === 'xs' ? 'text-[10px]' : 'text-xs'}`}>
          ({rating > 0 ? rating.toFixed(1) : '0'}) {count}
        </span>
      )}
      {showCount && count === 0 && (
        <span className={`text-slate-400 ${size === 'xs' ? 'text-[10px]' : 'text-xs'}`}>Sin valoraciones</span>
      )}
    </div>
  );
}
