'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { User, Mail, Briefcase, Shield, Settings, Save, Camera } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ContentArea } from '@/components/layout';
import { useUserStore } from '@/stores/userStore';
import { useNavigation } from '@/hooks/useNavigation';

export default function ProfilePage() {
  const { profile, isAuthenticated, updateProfile } = useUserStore();
  const { navigateTo } = useNavigation();
  const [isEditing, setIsEditing] = useState(false);
  const [editedProfile, setEditedProfile] = useState(profile);

  if (!isAuthenticated || !profile) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="p-8 text-center">
          <h2 className="text-xl font-semibold mb-4">Authentication Required</h2>
          <p className="text-muted-foreground mb-4">
            Please log in to view your profile.
          </p>
          <Button onClick={() => navigateTo('/')}>
            Go to Home
          </Button>
        </Card>
      </div>
    );
  }

  const handleSave = () => {
    if (editedProfile) {
      updateProfile(editedProfile);
      setIsEditing(false);
    }
  };

  const handleCancel = () => {
    setEditedProfile(profile);
    setIsEditing(false);
  };

  const handleInputChange = (field: keyof typeof profile, value: string) => {
    if (editedProfile) {
      setEditedProfile({
        ...editedProfile,
        [field]: value,
      });
    }
  };

  return (
    <ContentArea className="max-w-4xl">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Profile</h1>
            <p className="text-muted-foreground mt-1">
              Manage your account information and preferences
            </p>
          </div>
          <div className="flex space-x-2">
            <Button
              variant="outline"
              onClick={() => navigateTo('/profile/settings')}
              className="flex items-center space-x-2"
            >
              <Settings className="h-4 w-4" />
              <span>Settings</span>
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Profile Card */}
          <div className="lg:col-span-1">
            <Card className="p-6">
              <div className="text-center">
                {/* Avatar */}
                <div className="relative inline-block mb-4">
                  {profile.avatar ? (
                    <img
                      src={profile.avatar}
                      alt={profile.name}
                      className="w-24 h-24 rounded-full object-cover mx-auto"
                    />
                  ) : (
                    <div className="w-24 h-24 rounded-full bg-primary flex items-center justify-center mx-auto">
                      <User className="h-12 w-12 text-primary-foreground" />
                    </div>
                  )}
                  {isEditing && (
                    <Button
                      size="sm"
                      variant="secondary"
                      className="absolute bottom-0 right-0 rounded-full h-8 w-8 p-0"
                      aria-label="Change avatar"
                    >
                      <Camera className="h-4 w-4" />
                    </Button>
                  )}
                </div>

                {/* Name and Role */}
                <h2 className="text-xl font-semibold text-foreground mb-1">
                  {profile.name}
                </h2>
                <p className="text-muted-foreground mb-3">{profile.role}</p>
                
                {/* Authentication Status */}
                <Badge variant="secondary" className="mb-4">
                  <Shield className="h-3 w-3 mr-1" />
                  Authenticated
                </Badge>

                {/* Edit Toggle */}
                {!isEditing ? (
                  <Button
                    onClick={() => setIsEditing(true)}
                    className="w-full"
                  >
                    Edit Profile
                  </Button>
                ) : (
                  <div className="space-y-2">
                    <Button
                      onClick={handleSave}
                      className="w-full"
                    >
                      <Save className="h-4 w-4 mr-2" />
                      Save Changes
                    </Button>
                    <Button
                      variant="outline"
                      onClick={handleCancel}
                      className="w-full"
                    >
                      Cancel
                    </Button>
                  </div>
                )}
              </div>
            </Card>
          </div>

          {/* Profile Details */}
          <div className="lg:col-span-2">
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-6">Profile Information</h3>
              
              <div className="space-y-6">
                {/* Name Field */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Full Name
                  </label>
                  {isEditing ? (
                    <input
                      type="text"
                      value={editedProfile?.name || ''}
                      onChange={(e) => handleInputChange('name', e.target.value)}
                      className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                      placeholder="Enter your full name"
                    />
                  ) : (
                    <div className="flex items-center space-x-2 p-3 bg-muted rounded-md">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <span>{profile.name}</span>
                    </div>
                  )}
                </div>

                {/* Email Field */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Email Address
                  </label>
                  {isEditing ? (
                    <input
                      type="email"
                      value={editedProfile?.email || ''}
                      onChange={(e) => handleInputChange('email', e.target.value)}
                      className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                      placeholder="Enter your email address"
                    />
                  ) : (
                    <div className="flex items-center space-x-2 p-3 bg-muted rounded-md">
                      <Mail className="h-4 w-4 text-muted-foreground" />
                      <span>{profile.email}</span>
                    </div>
                  )}
                </div>

                {/* Role Field */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Role
                  </label>
                  {isEditing ? (
                    <input
                      type="text"
                      value={editedProfile?.role || ''}
                      onChange={(e) => handleInputChange('role', e.target.value)}
                      className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                      placeholder="Enter your role"
                    />
                  ) : (
                    <div className="flex items-center space-x-2 p-3 bg-muted rounded-md">
                      <Briefcase className="h-4 w-4 text-muted-foreground" />
                      <span>{profile.role}</span>
                    </div>
                  )}
                </div>

                {/* User ID (Read-only) */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    User ID
                  </label>
                  <div className="flex items-center space-x-2 p-3 bg-muted rounded-md">
                    <Shield className="h-4 w-4 text-muted-foreground" />
                    <span className="font-mono text-sm">{profile.id}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    This is your unique identifier and cannot be changed.
                  </p>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </motion.div>
    </ContentArea>
  );
}