'use client';

import Link from 'next/link';
import { CalendarDays, RefreshCw, ShieldCheck, UserCircle2 } from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { useAuthStore } from '@/stores';

function formatDateTime(value?: string) {
  if (!value) return '暂无';

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

export default function ProfilePage() {
  const { user, refreshUser, isLoading } = useAuthStore();
  const roleLabel = !user ? '未登录' : user.role === 'admin' ? '管理员' : '普通用户';

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-medium text-primary-600">Profile</p>
          <h1 className="mt-1 text-3xl font-bold text-gray-900 dark:text-white">个人设置</h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            查看当前账号信息，并快速跳转到聊天、知识库和召回测试功能。
          </p>
        </div>
        <Button onClick={() => refreshUser()} loading={isLoading}>
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新资料
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserCircle2 className="h-5 w-5 text-primary-600" />
              账户信息
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/40">
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">用户名</p>
                <p className="mt-2 text-base font-semibold text-gray-900 dark:text-white">{user?.username || '暂无'}</p>
              </div>
              <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/40">
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">邮箱</p>
                <p className="mt-2 text-base font-semibold text-gray-900 dark:text-white">{user?.email || '暂无'}</p>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-gray-200 p-4 dark:border-gray-700">
                <div className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                  <ShieldCheck className="h-4 w-4 text-primary-600" />
                  当前角色
                </div>
                <p className="mt-2 text-lg font-semibold text-gray-900 dark:text-white">{roleLabel}</p>
              </div>
              <div className="rounded-xl border border-gray-200 p-4 dark:border-gray-700">
                <div className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                  <CalendarDays className="h-4 w-4 text-primary-600" />
                  创建时间
                </div>
                <p className="mt-2 text-lg font-semibold text-gray-900 dark:text-white">
                  {formatDateTime(user?.created_at)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>快捷入口</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Link
              href="/chat"
              className="block rounded-xl border border-gray-200 p-4 transition-colors hover:border-primary-500 hover:bg-primary-50 dark:border-gray-700 dark:hover:border-primary-500 dark:hover:bg-primary-900/20"
            >
              <p className="text-sm font-semibold text-gray-900 dark:text-white">继续对话</p>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">进入机器人聊天页面，继续发起 RAG 问答。</p>
            </Link>
            <Link
              href="/knowledge"
              className="block rounded-xl border border-gray-200 p-4 transition-colors hover:border-primary-500 hover:bg-primary-50 dark:border-gray-700 dark:hover:border-primary-500 dark:hover:bg-primary-900/20"
            >
              <p className="text-sm font-semibold text-gray-900 dark:text-white">管理知识库</p>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">查看文档入库状态、切片和向量化结果。</p>
            </Link>
            <Link
              href="/recall/test"
              className="block rounded-xl border border-gray-200 p-4 transition-colors hover:border-primary-500 hover:bg-primary-50 dark:border-gray-700 dark:hover:border-primary-500 dark:hover:bg-primary-900/20"
            >
              <p className="text-sm font-semibold text-gray-900 dark:text-white">运行召回测试</p>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">提交批量 query，查看召回率、精确率和 Top-N 命中情况。</p>
            </Link>
            {user?.role === 'admin' && (
              <Link
                href="/admin/llms"
                className="block rounded-xl border border-gray-200 p-4 transition-colors hover:border-primary-500 hover:bg-primary-50 dark:border-gray-700 dark:hover:border-primary-500 dark:hover:bg-primary-900/20"
              >
                <p className="text-sm font-semibold text-gray-900 dark:text-white">管理模型配置</p>
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">查看聊天、嵌入和重排模型，以及对应的 API 密钥绑定。</p>
              </Link>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
