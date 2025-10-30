import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Home, Shield, FileText, User } from 'lucide-react';
import { NavigationItem } from '@/types/navigation';

interface NavigationState {
  isCollapsed: boolean;
  currentRoute: string;
  navigationItems: NavigationItem[];
  toggleCollapse: () => void;
  setCurrentRoute: (route: string) => void;
}

const defaultNavigationItems: NavigationItem[] = [
  {
    id: 'home',
    label: 'Home',
    icon: Home,
    route: '/',
  },
  {
    id: 'compliance',
    label: 'Compliance',
    icon: Shield,
    route: '/compliance',
  },
  {
    id: 'documents',
    label: 'Documents',
    icon: FileText,
    route: '/documents',
  },
  {
    id: 'profile',
    label: 'Profile',
    icon: User,
    route: '/profile',
  },
];

export const useNavigationStore = create<NavigationState>()(
  persist(
    (set) => ({
      isCollapsed: false,
      currentRoute: '/',
      navigationItems: defaultNavigationItems,
      toggleCollapse: () =>
        set((state) => ({ isCollapsed: !state.isCollapsed })),
      setCurrentRoute: (route: string) =>
        set({ currentRoute: route }),
    }),
    {
      name: 'navigation-storage',
      partialize: (state) => ({ isCollapsed: state.isCollapsed }),
    }
  )
);