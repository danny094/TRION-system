import { Search, Menu } from 'lucide-react'

export function SearchBar() {
  return (
    <div className="absolute top-12 left-1/2 -translate-x-1/2 w-full max-w-xl z-50">
      <div className="relative group">
        <div className="absolute inset-0 bg-primary/20 blur-2xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
        <div className="relative flex items-center bg-black/50 backdrop-blur-2xl border border-white/10 rounded-[2rem] px-6 py-4 shadow-[0_8px_32px_rgba(0,0,0,0.4)]">
          <Menu className="w-5 h-5 text-white/50 mr-4 cursor-pointer hover:text-white/80 transition-colors" />
          <input 
            type="text" 
            placeholder="Suche Apps, Tools und Funktionen..." 
            className="w-full bg-transparent border-none outline-none text-white/90 placeholder:text-white/30 text-base font-medium tracking-wide"
          />
          <Search className="w-5 h-5 text-white/40 ml-4" />
        </div>
      </div>
    </div>
  )
}
