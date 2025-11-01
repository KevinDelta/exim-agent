'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { User, Settings, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useUserStore } from '@/stores/userStore';
import { useNavigation } from '@/hooks/useNavigation';

interface ProfileSectionProps {
  isCollapsed: boolean;
}

export function ProfileSection({ isCollapsed }: ProfileSectionProps) {
  const { profile, isAuthenticated } = useUserStore();
  const { navigateTo } = useNavigation();

  const handleProfileClick = () => {
    navigateTo('/profile');
  };

  const handleSettingsClick = () => {
    navigateTo('/profile/settings');
  };

  const handleLogoutClick = () => {
    // TODO: Implement actual logout logic
    console.log('Logout functionality to be implemented');
  };

  if (!isAuthenticated || !profile) {
    return null;
  }

  return (
    <div className="border-t border-border p-3" role="region" aria-label="User profile">
      {isCollapsed ? (
        // Collapsed state - just avatar
        <div className="flex justify-center">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleProfileClick}
            className="h-10 w-10 rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            aria-label={`View profile for ${profile.name}, ${profile.role}`}
            title={`${profile.name} - ${profile.role}`}
            type="button"
          >
            {profile.avatar ? (
              <img
                src={profile.avatar}
                alt={profile.name}
                className="h-8 w-8 rounded-full object-cover"
              />
            ) : (
              <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
                <User className="h-4 w-4 text-primary-foreground" />
              </div>
            )}
          </Button>
        </div>
      ) : (
        // Expanded state - full profile info
        <AnimatePresence mode="wait">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.2 }}
            className="space-y-3"
          >
            {/* User info */}
            <Button
              variant="ghost"
              onClick={handleProfileClick}
              className="w-full justify-start p-2 h-auto focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              aria-label={`View profile for ${profile.name}, ${profile.role}`}
              type="button"
            >
              <div className="flex items-center space-x-3">
                {profile.avatar ? (
                  <img
                    src={profile.avatar}
                    alt={profile.name}
                    className="h-10 w-10 rounded-full object-cover"
                  />
                ) : (
                  <div className="h-10 w-10 rounded-full bg-primary flex items-center justify-center">
                    <User className="h-5 w-5 text-primary-foreground" />
                  </div>
                )}
                <div className="flex flex-col items-start min-w-0 flex-1">
                  <span className="text-sm font-medium text-foreground truncate">
                    {profile.name}
                  </span>
                  <span className="text-xs text-muted-foreground truncate">
                    {profile.role}
                  </span>
                </div>
              </div>
            </Button>

            {/* Action buttons */}
            <div className="flex space-x-1" role="group" aria-label="Profile actions">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleSettingsClick}
                className="flex-1 justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                aria-label="Open account settings"
                title="Account Settings"
                type="button"
              >
                <Settings className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogoutClick}
                className="flex-1 justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                aria-label="Sign out of account"
                title="Sign Out"
                type="button"
              >
                <LogOut className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </motion.div>
        </AnimatePresence>
      )}
    </div>
  );
}