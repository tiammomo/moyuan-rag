'use client';

import type { ReactNode } from 'react';
import { MainLayout } from '@/components/layout/main-layout';

interface AdminLayoutProps {
  children: ReactNode;
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  return <MainLayout>{children}</MainLayout>;
}
