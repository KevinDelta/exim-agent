'use client';

import { useRouter, usePathname } from 'next/navigation';
import { useNavigationStore } from '@/stores/navigationStore';
import { useEffect } from 'react';

export function useNavigation() {
  const router = useRouter();
  const pathname = usePathname();
  const { 
    isCollapsed, 
    currentRoute, 
    navigationItems, 
    toggleCollapse, 
    setCurrentRoute 
  } = useNavigationStore();

  // Sync current route with pathname
  useEffect(() => {
    if (pathname !== currentRoute) {
      setCurrentRoute(pathname);
    }
  }, [pathname, currentRoute, setCurrentRoute]);

  const navigateTo = (route: string) => {
    setCurrentRoute(route);
    router.push(route);
  };

  const isActiveRoute = (route: string) => {
    return currentRoute === route;
  };

  const getActiveNavigationItem = () => {
    return navigationItems.find(item => item.route === currentRoute);
  };

  return {
    // State
    isCollapsed,
    currentRoute,
    navigationItems,
    
    // Actions
    toggleCollapse,
    navigateTo,
    setCurrentRoute,
    
    // Helpers
    isActiveRoute,
    getActiveNavigationItem,
  };
}