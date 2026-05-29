import { create } from 'zustand';
import Cookie from 'js-cookie';

interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

interface AuthStore {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  setAuthenticated: (auth: boolean) => void;
  setLoading: (loading: boolean) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  isAuthenticated: !!Cookie.get('access_token'),
  isLoading: false,
  setUser: (user) => set({ user }),
  setAuthenticated: (auth) => set({ isAuthenticated: auth }),
  setLoading: (loading) => set({ isLoading: loading }),
  logout: () => {
    Cookie.remove('access_token');
    Cookie.remove('refresh_token');
    set({ user: null, isAuthenticated: false });
  },
}));

interface SearchStore {
  searchQuery: string;
  searchResults: any[];
  isSearching: boolean;
  searchHistory: any[];
  setSearchQuery: (query: string) => void;
  setSearchResults: (results: any[]) => void;
  setIsSearching: (searching: boolean) => void;
  setSearchHistory: (history: any[]) => void;
  clearSearch: () => void;
}

export const useSearchStore = create<SearchStore>((set) => ({
  searchQuery: '',
  searchResults: [],
  isSearching: false,
  searchHistory: [],
  setSearchQuery: (query) => set({ searchQuery: query }),
  setSearchResults: (results) => set({ searchResults: results }),
  setIsSearching: (searching) => set({ isSearching: searching }),
  setSearchHistory: (history) => set({ searchHistory: history }),
  clearSearch: () => set({ searchQuery: '', searchResults: [] }),
}));

interface UIStore {
  isDarkMode: boolean;
  sidebarOpen: boolean;
  toggleDarkMode: () => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  isDarkMode: true,
  sidebarOpen: true,
  toggleDarkMode: () => set((state) => ({ isDarkMode: !state.isDarkMode })),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}));
