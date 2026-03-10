export function BadgeDisplay({ badges = [], size = 'sm' }) {
  if (!badges.length) return null;
  const sizeClasses = { xs: 'text-xs px-1.5 py-0.5', sm: 'text-xs px-2 py-1', md: 'text-sm px-2.5 py-1' };
  const cls = sizeClasses[size] || sizeClasses.sm;
  return (
    <div className="flex flex-wrap gap-1" data-testid="badge-display">
      {badges.map((b) => (
        <span
          key={b.id || b.name}
          className={`inline-flex items-center gap-1 rounded-full bg-slate-100 text-slate-700 ${cls} cursor-default`}
          title={b.description}
          data-testid={`badge-${b.id || b.name}`}
        >
          <span>{b.emoji}</span>
          <span className="font-medium">{b.name}</span>
        </span>
      ))}
    </div>
  );
}
