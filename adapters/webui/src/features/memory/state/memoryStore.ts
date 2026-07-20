import { create } from 'zustand'
import type { SearchMode } from '../contracts'

export type MemoryView = 'recent' | 'search' | 'conversations'

interface MemoryUiState {
  view: MemoryView
  selectedConversationId: string | null
  searchQuery: string
  searchMode: SearchMode
  setView: (view: MemoryView) => void
  selectConversation: (id: string | null) => void
  setSearchQuery: (query: string) => void
  setSearchMode: (mode: SearchMode) => void
}

export const useMemoryStore = create<MemoryUiState>((set) => ({
  view: 'recent',
  selectedConversationId: null,
  searchQuery: '',
  searchMode: 'fts',
  setView: (view) => set({ view }),
  selectConversation: (id) => set({ selectedConversationId: id }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  setSearchMode: (searchMode) => set({ searchMode }),
}))
