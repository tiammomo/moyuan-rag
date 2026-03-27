'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore, useThemeStore } from '@/stores';
import { Header } from './header';

interface MainLayoutProps {
  children: React.ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, refreshUser } = useAuthStore();
  const { theme } = useThemeStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;

    const root = document.documentElement;
    const prefersDark =
      theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);

    if (prefersDark) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [theme, mounted]);

  useEffect(() => {
    if (!mounted) return;

    const publicPaths = ['/auth/login', '/auth/register'];
    const isPublicPath = publicPaths.some((path) => pathname.startsWith(path));
    const storedToken = typeof window !== 'undefined' ? localStorage.getItem('token') : null;

    if (storedToken && !isAuthenticated && !isPublicPath) {
      refreshUser();
      return;
    }

    if (!isAuthenticated && !storedToken && !isPublicPath) {
      router.push('/auth/login');
    }
  }, [isAuthenticated, mounted, pathname, refreshUser, router]);

  if (!mounted) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (pathname.startsWith('/auth/')) {
    return <>{children}</>;
  }

  if (!isAuthenticated) {
    if (typeof window !== 'undefined' && localStorage.getItem('token')) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
          <div className="text-gray-500">验证身份中...</div>
        </div>
      );
    }

    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Header />
      <main className="flex-1">{children}</main>
    </div>
  );
}
