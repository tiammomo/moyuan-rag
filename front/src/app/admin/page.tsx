'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Cpu, Key, ScrollText, ShieldCheck, Users } from 'lucide-react';
import { useAuthStore } from '@/stores/auth-store';
import { Card, CardContent } from '@/components/ui/card';

export default function AdminPage() {
  const router = useRouter();
  const { user } = useAuthStore();

  useEffect(() => {
    if (user?.role !== 'admin') {
      router.push('/chat');
    }
  }, [router, user]);

  if (user?.role !== 'admin') {
    return null;
  }

  const adminModules = [
    {
      title: '用户管理',
      description: '查看和维护系统用户、角色和状态。',
      icon: Users,
      href: '/admin/users',
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-100 dark:bg-blue-900/40',
    },
    {
      title: 'LLM 配置',
      description: '管理聊天、Embedding 和 Rerank 模型配置。',
      icon: Cpu,
      href: '/admin/llms',
      color: 'text-green-600 dark:text-green-400',
      bgColor: 'bg-green-100 dark:bg-green-900/40',
    },
    {
      title: 'API 密钥',
      description: '维护模型访问密钥和绑定关系。',
      icon: Key,
      href: '/admin/apikeys',
      color: 'text-purple-600 dark:text-purple-400',
      bgColor: 'bg-purple-100 dark:bg-purple-900/40',
    },
    {
      title: 'Skills 治理',
      description: '查看安装任务、审计日志、版本差异和回滚准备信息。',
      icon: ShieldCheck,
      href: '/admin/skills',
      color: 'text-amber-600 dark:text-amber-300',
      bgColor: 'bg-amber-100 dark:bg-amber-900/40',
    },
  ];

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8">
      <div>
        <div className="inline-flex items-center gap-2 rounded-full border border-primary-200 bg-primary-50 px-3 py-1 text-xs font-medium text-primary-700 dark:border-primary-800 dark:bg-primary-900/30 dark:text-primary-300">
          <ScrollText className="h-3.5 w-3.5" />
          Admin Console
        </div>
        <h1 className="mt-4 text-3xl font-bold text-gray-900 dark:text-white">管理员控制台</h1>
        <p className="mt-2 max-w-2xl text-sm text-gray-600 dark:text-gray-400">
          这里汇总系统治理入口。你可以在这里管理用户、模型、API 密钥，以及 skills 安装与审计数据。
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        {adminModules.map((module) => (
          <Link key={module.href} href={module.href}>
            <Card className="h-full border-gray-200 transition-all hover:-translate-y-0.5 hover:shadow-lg dark:border-gray-700">
              <CardContent className="p-6">
                <div className={`mb-4 flex h-12 w-12 items-center justify-center rounded-xl ${module.bgColor}`}>
                  <module.icon className={`h-6 w-6 ${module.color}`} />
                </div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{module.title}</h2>
                <p className="mt-2 text-sm leading-6 text-gray-600 dark:text-gray-400">{module.description}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
