import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiRequest } from '@/lib/api';

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  billing_plan: string;
  monthly_call_limit: number;
}

interface AuthContextType {
  user: User | null;
  organization: Organization | null;
  role: string | null;
  token: string | null;
  isLoading: boolean;
  isDemoMode: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, fullName: string, password: string, orgName?: string) => Promise<void>;
  logout: () => void;
  setDemoMode: (val: boolean) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('serviceforce_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(() => localStorage.getItem('serviceforce_demo') !== 'false');

  useEffect(() => {
    async function loadProfile() {
      const storedToken = localStorage.getItem('serviceforce_token');
      if (!storedToken) {
        setIsLoading(false);
        return;
      }
      try {
        const data = await apiRequest<{ user: User; organization: Organization; role: string }>('/auth/me');
        setUser(data.user);
        setOrganization(data.organization);
        setRole(data.role);
        localStorage.setItem('serviceforce_org_id', data.organization.id);
      } catch (err) {
        console.error('Failed to restore session:', err);
        localStorage.removeItem('serviceforce_token');
        localStorage.removeItem('serviceforce_org_id');
        setToken(null);
        setUser(null);
        setOrganization(null);
        setRole(null);
      } finally {
        setIsLoading(false);
      }
    }
    loadProfile();
  }, [token]);

  const login = async (email: string, password: string) => {
    const data = await apiRequest<{
      access_token: string;
      user: User;
      organization_id: string;
      organization_name: string;
      role: string;
    }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    localStorage.setItem('serviceforce_token', data.access_token);
    localStorage.setItem('serviceforce_org_id', data.organization_id);
    setToken(data.access_token);
    setUser(data.user);
    setRole(data.role);
    setOrganization({
      id: data.organization_id,
      name: data.organization_name,
      slug: data.organization_name.toLowerCase().replace(/\s+/g, '-'),
      billing_plan: 'starter',
      monthly_call_limit: 500,
    });
  };

  const register = async (email: string, fullName: string, password: string, orgName?: string) => {
    const data = await apiRequest<{
      access_token: string;
      user: User;
      organization_id: string;
      organization_name: string;
      role: string;
    }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        email,
        full_name: fullName,
        password,
        organization_name: orgName || `${fullName}'s Business`,
      }),
    });

    localStorage.setItem('serviceforce_token', data.access_token);
    localStorage.setItem('serviceforce_org_id', data.organization_id);
    setToken(data.access_token);
    setUser(data.user);
    setRole(data.role);
    setOrganization({
      id: data.organization_id,
      name: data.organization_name,
      slug: data.organization_name.toLowerCase().replace(/\s+/g, '-'),
      billing_plan: 'starter',
      monthly_call_limit: 500,
    });
  };

  const logout = () => {
    localStorage.removeItem('serviceforce_token');
    localStorage.removeItem('serviceforce_org_id');
    setToken(null);
    setUser(null);
    setOrganization(null);
    setRole(null);
  };

  const setDemoMode = (val: boolean) => {
    setIsDemoMode(val);
    localStorage.setItem('serviceforce_demo', val ? 'true' : 'false');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        organization,
        role,
        token,
        isLoading,
        isDemoMode,
        login,
        register,
        logout,
        setDemoMode,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
