// User state management using Zustand

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { UserState, UserProfile, UserPreferences } from '@/types/navigation';

// Default user preferences
const defaultPreferences: UserPreferences = {
  theme: 'system',
  navigationCollapsed: false,
  chatExpanded: false,
  notifications: true,
};

// Mock user profile for development
const mockUserProfile: UserProfile = {
  id: 'user_1',
  name: 'Compliance User',
  email: 'user@compliance.com',
  role: 'Compliance Analyst',
  isAuthenticated: true,
};

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      profile: mockUserProfile, // In production, this would be null initially
      isAuthenticated: true, // In production, this would be false initially
      preferences: defaultPreferences,
      
      updateProfile: (profileUpdate: Partial<UserProfile>) => {
        set((state) => ({
          profile: state.profile 
            ? { ...state.profile, ...profileUpdate }
            : null,
        }));
      },
      
      setPreferences: (preferences: UserPreferences) => {
        set({ preferences });
      },
    }),
    {
      name: 'user-storage',
      partialize: (state) => ({ 
        profile: state.profile,
        isAuthenticated: state.isAuthenticated,
        preferences: state.preferences,
      }),
    }
  )
);