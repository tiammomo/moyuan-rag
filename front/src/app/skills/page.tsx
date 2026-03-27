'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { Search, Upload, Wrench, PackageCheck, ShieldAlert } from 'lucide-react';
import toast from 'react-hot-toast';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { EmptyState, PageLoading } from '@/components/ui/loading';
import { skillApi } from '@/api';
import { formatDateTime } from '@/lib/utils';
import { useAuthStore } from '@/stores';
import type { SkillListItem } from '@/types';

export default function SkillsPage() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { user } = useAuthStore();
  const [skills, setSkills] = useState<SkillListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [installing, setInstalling] = useState(false);
  const [keyword, setKeyword] = useState('');

  const loadSkills = async () => {
    setLoading(true);
    try {
      const data = await skillApi.getList();
      setSkills(data.items);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '加载 skills 列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSkills();
  }, []);

  const filteredSkills = useMemo(() => {
    const lowered = keyword.trim().toLowerCase();
    if (!lowered) return skills;
    return skills.filter((skill) =>
      [skill.name, skill.slug, skill.category || '', skill.description || '']
        .join(' ')
        .toLowerCase()
        .includes(lowered)
    );
  }, [keyword, skills]);

  const handleInstallClick = () => {
    fileInputRef.current?.click();
  };

  const handleLocalInstall = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    setInstalling(true);
    try {
      const response = await skillApi.installLocal(file);
      toast.success(`Skill 安装成功：${response.skill.name}`);
      await loadSkills();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Skill 安装失败');
    } finally {
      setInstalling(false);
    }
  };

  if (loading) {
    return <PageLoading text="加载 skills 中..." />;
  }

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Skills</h1>
          <p className="mt-1 text-gray-500 dark:text-gray-400">
            这里展示当前仓库已安装的本地 skill 包，以及它们与机器人之间的绑定情况。
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative min-w-[260px]">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              placeholder="搜索 skill 名称、slug 或分类"
              className="w-full rounded-lg border border-gray-300 py-2 pl-9 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
            />
          </div>
          {user?.role === 'admin' && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".zip"
                onChange={handleLocalInstall}
              />
              <Button onClick={handleInstallClick} loading={installing}>
                <Upload className="mr-2 h-4 w-4" />
                安装本地 skill
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-200">
        <div className="flex items-start gap-3">
          <ShieldAlert className="mt-0.5 h-4 w-4 flex-none" />
          <div>
            <p className="font-medium">远端安装默认关闭</p>
            <p className="mt-1">
              当前 bootstrap 版本只开放本地 zip 包安装。远端 skill 下载需要显式开启
              `ENABLE_REMOTE_SKILL_INSTALL`，并且仍不属于默认运行路径。
            </p>
          </div>
        </div>
      </div>

      {filteredSkills.length === 0 ? (
        <EmptyState
          icon={<Wrench className="h-12 w-12" />}
          title="还没有可展示的 skills"
          description="先安装本地 skill 包，或者检查 backend/data/skills/registry 下的本地注册表。"
          action={
            user?.role === 'admin' ? (
              <Button onClick={handleInstallClick} loading={installing}>
                <Upload className="mr-2 h-4 w-4" />
                安装本地 skill
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {filteredSkills.map((skill) => (
            <Link key={skill.slug} href={`/skills/${skill.slug}`}>
              <Card className="h-full transition-shadow hover:shadow-md">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary-100 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300">
                        <PackageCheck className="h-5 w-5" />
                      </div>
                      <div>
                        <CardTitle className="text-lg">{skill.name}</CardTitle>
                        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{skill.slug}</p>
                      </div>
                    </div>
                    <span className="rounded-full bg-green-50 px-2.5 py-1 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-300">
                      {skill.status}
                    </span>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="min-h-[44px] text-sm text-gray-600 dark:text-gray-400">
                    {skill.description || '暂无描述'}
                  </p>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="rounded-lg border border-gray-200 px-3 py-2 dark:border-gray-700">
                      <p className="text-xs text-gray-500">版本</p>
                      <p className="mt-1 font-medium text-gray-900 dark:text-white">{skill.version}</p>
                    </div>
                    <div className="rounded-lg border border-gray-200 px-3 py-2 dark:border-gray-700">
                      <p className="text-xs text-gray-500">分类</p>
                      <p className="mt-1 font-medium text-gray-900 dark:text-white">{skill.category || '未分类'}</p>
                    </div>
                    <div className="rounded-lg border border-gray-200 px-3 py-2 dark:border-gray-700">
                      <p className="text-xs text-gray-500">来源</p>
                      <p className="mt-1 font-medium text-gray-900 dark:text-white">{skill.source_type}</p>
                    </div>
                    <div className="rounded-lg border border-gray-200 px-3 py-2 dark:border-gray-700">
                      <p className="text-xs text-gray-500">已绑定机器人</p>
                      <p className="mt-1 font-medium text-gray-900 dark:text-white">{skill.bound_robot_count}</p>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500">安装时间：{skill.installed_at ? formatDateTime(skill.installed_at) : '未知'}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
