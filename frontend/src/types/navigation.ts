import { LucideIcon } from 'lucide-react';

export interface NavigationItem {
  id: string;
  label: string;
  icon: LucideIcon;
  route: string;
  badge?: number;
  disabled?: boolean;
}

export interface SideNavigationProps {
  isCollapsed: boolean;
  onToggle: () => void;
  currentRoute: string;
}

export interface NavigationItemProps {
  item: NavigationItem;
  isActive: boolean;
  isCollapsed: boolean;
  onClick: (route: string) => void;
  tabIndex?: number;
  ariaSetSize?: number;
  ariaPosInSet?: number;
}

export interface NavigationToggleProps {
  isCollapsed: boolean;
  onToggle: () => void;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  role: string;
  isAuthenticated: boolean;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  navigationCollapsed: boolean;
  chatExpanded: boolean;
  notifications: boolean;
}

export interface UserState {
  profile: UserProfile | null;
  isAuthenticated: boolean;
  preferences: UserPreferences;
  updateProfile: (profile: Partial<UserProfile>) => void;
  setPreferences: (preferences: UserPreferences) => void;
}