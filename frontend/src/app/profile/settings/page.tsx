'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Settings, 
  Moon, 
  Sun, 
  Monitor, 
  Bell, 
  BellOff, 
  Navigation, 
  MessageSquare,
  Save,
  ArrowLeft
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ContentArea } from '@/components/layout';
import { useUserStore } from '@/stores/userStore';
import { useNavigation } from '@/hooks/useNavigation';
import { UserPreferences } from '@/types/navigation';

export default function SettingsPage() {
  const { profile, isAuthenticated, preferences, setPreferences } = useUserStore();
  const { navigateTo } = useNavigation();
  const [editedPreferences, setEditedPreferences] = useState<UserPreferences>(preferences);
  const [hasChanges, setHasChanges] = useState(false);

  if (!isAuthenticated || !profile) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="p-8 text-center">
          <h2 className="text-xl font-semibold mb-4">Authentication Required</h2>
          <p className="text-muted-foreground mb-4">
            Please log in to access settings.
          </p>
          <Button onClick={() => navigateTo('/')}>
            Go to Home
          </Button>
        </Card>
      </div>
    );
  }

  const handlePreferenceChange = <K extends keyof UserPreferences>(
    key: K,
    value: UserPreferences[K]
  ) => {
    const newPreferences = {
      ...editedPreferences,
      [key]: value,
    };
    setEditedPreferences(newPreferences);
    setHasChanges(JSON.stringify(newPreferences) !== JSON.stringify(preferences));
  };

  const handleSave = () => {
    setPreferences(editedPreferences);
    setHasChanges(false);
  };

  const handleReset = () => {
    setEditedPreferences(preferences);
    setHasChanges(false);
  };

  const themeOptions = [
    { value: 'light' as const, label: 'Light', icon: Sun },
    { value: 'dark' as const, label: 'Dark', icon: Moon },
    { value: 'system' as const, label: 'System', icon: Monitor },
  ];

  return (
    <ContentArea className="max-w-4xl">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigateTo('/profile')}
              className="flex items-center space-x-2"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>Back to Profile</span>
            </Button>
            <div>
              <h1 className="text-3xl font-bold text-foreground">Settings</h1>
              <p className="text-muted-foreground mt-1">
                Customize your experience and preferences
              </p>
            </div>
          </div>
          
          {hasChanges && (
            <div className="flex space-x-2">
              <Button variant="outline" onClick={handleReset}>
                Reset
              </Button>
              <Button onClick={handleSave} className="flex items-center space-x-2">
                <Save className="h-4 w-4" />
                <span>Save Changes</span>
              </Button>
            </div>
          )}
        </div>

        <div className="space-y-6">
          {/* Appearance Settings */}
          <Card className="p-6">
            <div className="flex items-center space-x-2 mb-4">
              <Settings className="h-5 w-5 text-primary" />
              <h2 className="text-xl font-semibold">Appearance</h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-3">
                  Theme Preference
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {themeOptions.map((option) => {
                    const Icon = option.icon;
                    const isSelected = editedPreferences.theme === option.value;
                    
                    return (
                      <button
                        key={option.value}
                        onClick={() => handlePreferenceChange('theme', option.value)}
                        className={`
                          p-4 rounded-lg border-2 transition-all duration-200 flex flex-col items-center space-y-2
                          ${isSelected 
                            ? 'border-primary bg-primary/10 text-primary' 
                            : 'border-border hover:border-primary/50 hover:bg-muted'
                          }
                        `}
                      >
                        <Icon className="h-6 w-6" />
                        <span className="text-sm font-medium">{option.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </Card>

          {/* Navigation Settings */}
          <Card className="p-6">
            <div className="flex items-center space-x-2 mb-4">
              <Navigation className="h-5 w-5 text-primary" />
              <h2 className="text-xl font-semibold">Navigation</h2>
            </div>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-sm font-medium text-foreground">
                    Default Navigation State
                  </label>
                  <p className="text-xs text-muted-foreground mt-1">
                    Choose whether the navigation menu starts collapsed or expanded
                  </p>
                </div>
                <Button
                  variant={editedPreferences.navigationCollapsed ? "default" : "outline"}
                  size="sm"
                  onClick={() => handlePreferenceChange('navigationCollapsed', !editedPreferences.navigationCollapsed)}
                >
                  {editedPreferences.navigationCollapsed ? 'Collapsed' : 'Expanded'}
                </Button>
              </div>
            </div>
          </Card>

          {/* Chat Settings */}
          <Card className="p-6">
            <div className="flex items-center space-x-2 mb-4">
              <MessageSquare className="h-5 w-5 text-primary" />
              <h2 className="text-xl font-semibold">Chat</h2>
            </div>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-sm font-medium text-foreground">
                    Default Chat State
                  </label>
                  <p className="text-xs text-muted-foreground mt-1">
                    Choose whether the chat interface starts expanded or collapsed
                  </p>
                </div>
                <Button
                  variant={editedPreferences.chatExpanded ? "default" : "outline"}
                  size="sm"
                  onClick={() => handlePreferenceChange('chatExpanded', !editedPreferences.chatExpanded)}
                >
                  {editedPreferences.chatExpanded ? 'Expanded' : 'Collapsed'}
                </Button>
              </div>
            </div>
          </Card>

          {/* Notification Settings */}
          <Card className="p-6">
            <div className="flex items-center space-x-2 mb-4">
              {editedPreferences.notifications ? (
                <Bell className="h-5 w-5 text-primary" />
              ) : (
                <BellOff className="h-5 w-5 text-muted-foreground" />
              )}
              <h2 className="text-xl font-semibold">Notifications</h2>
            </div>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-sm font-medium text-foreground">
                    Enable Notifications
                  </label>
                  <p className="text-xs text-muted-foreground mt-1">
                    Receive notifications for compliance updates and system alerts
                  </p>
                </div>
                <Button
                  variant={editedPreferences.notifications ? "default" : "outline"}
                  size="sm"
                  onClick={() => handlePreferenceChange('notifications', !editedPreferences.notifications)}
                  className="flex items-center space-x-2"
                >
                  {editedPreferences.notifications ? (
                    <>
                      <Bell className="h-4 w-4" />
                      <span>Enabled</span>
                    </>
                  ) : (
                    <>
                      <BellOff className="h-4 w-4" />
                      <span>Disabled</span>
                    </>
                  )}
                </Button>
              </div>
            </div>
          </Card>

          {/* Account Information */}
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-4">Account Information</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">User ID:</span>
                <span className="font-mono">{profile.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Email:</span>
                <span>{profile.email}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Role:</span>
                <span>{profile.role}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status:</span>
                <span className="text-green-600">Active</span>
              </div>
            </div>
          </Card>
        </div>
      </motion.div>
    </ContentArea>
  );
}