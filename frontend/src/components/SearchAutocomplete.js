import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';

export function SearchAutocomplete({ initialQuery = '', onSearch }) {
  const [query, setQuery] = useState(initialQuery);
  const [suggestions, setSuggestions] = useState([]);
  const [show, setShow] = useState(false);
  const [focused, setFocused] = useState(false);
  const navigate = useNavigate();
  const ref = useRef(null);
  const debounceRef = useRef(null);
  const API = process.env.REACT_APP_BACKEND_URL;

  const fetchSuggestions = useCallback(async (q) => {
    if (q.length < 2) { setSuggestions([]); return; }
    try {
      const res = await fetch(`${API}/api/subastas/autocomplete?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      setSuggestions(data);
      setShow(data.length > 0);
    } catch { setSuggestions([]); }
  }, [API]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchSuggestions(query), 250);
    return () => clearTimeout(debounceRef.current);
  }, [query, fetchSuggestions]);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setShow(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    setShow(false);
    onSearch?.(query);
  };

  return (
    <div ref={ref} className="relative w-full" data-testid="search-autocomplete">
      <form onSubmit={handleSubmit} className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => { setFocused(true); if (suggestions.length) setShow(true); }}
          placeholder="Buscar subastas..."
          className="w-full pl-12 pr-4 py-3 rounded-full border border-slate-200 focus:border-[#18b29c] focus:ring-2 focus:ring-[#18b29c]/20 outline-none text-sm transition-all"
          data-testid="search-input"
        />
      </form>
      {show && focused && suggestions.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white rounded-xl shadow-lg border border-slate-100 overflow-hidden z-50" data-testid="suggestions-dropdown">
          {suggestions.map((s) => (
            <button
              key={s.id}
              onClick={() => { setShow(false); navigate(`/subasta/${s.id}`); }}
              className="flex items-center gap-3 w-full px-4 py-2.5 hover:bg-slate-50 text-left transition-colors"
              data-testid={`suggestion-${s.id}`}
            >
              {s.images?.[0] && (
                <img src={s.images[0]} alt="" className="w-8 h-8 rounded-lg object-cover flex-shrink-0" />
              )}
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-800 truncate">{s.title}</p>
                <p className="text-xs text-[#18b29c] font-bold">{s.current_price?.toFixed(2)} &euro;</p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
