'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ArrowLeft, FileCode2, Link2, PackageCheck } from 'lucide-react';
import toast from 'react-hot-toast';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { EmptyState, PageLoading } from '@/components/ui/loading';
import { skillApi } from '@/api';
import { formatDateTime } from '@/lib/utils';
import type { SkillDetail } from '@/types';

export default function SkillDetailPage() {
  const params = useParams<{ slug: string }>();
  const slug = Array.isArray(params.slug) ? params.slug[0] : params.slug;
  const [skill, setSkill] = useState<SkillDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadSkill = async () => {
      if (!slug) return;
      setLoading(true);
      try {
        const data = await skillApi.getBySlug(slug);
        setSkill(data);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : '加载 skill 详情失败');
      } finally {
        setLoading(false);
      }
    };

    loadSkill();
  }, [slug]);

  if (loading) {
    return <PageLoading text="加载 skill 详情中..." />;
  }

  if (!skill) {
    return (
      <div className="container mx-auto px-4 py-6">
        <EmptyState title="未找到 skill" description="请返回列表页确认当前 slug 是否存在。" />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="mb-6">
        <Link
          href="/skills"
          className="mb-4 inline-flex items-center text-sm text-primary-600 transition-colors hover:text-primary-700"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          返回 skills 列表
        </Link>
        <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-100 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300">
              <PackageCheck className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">{skill.name}</h1>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{skill.slug}</p>
              <p className="mt-3 max-w-3xl text-sm text-gray-600 dark:text-gray-400">{skill.description || '暂无描述'}</p>
            </div>
          </div>
          <div className="grid min-w-[260px] grid-cols-2 gap-3 text-sm">
            <div className="rounded-xl border border-gray-200 px-4 py-3 dark:border-gray-700">
              <p className="text-xs text-gray-500">版本</p>
              <p className="mt-1 font-medium text-gray-900 dark:text-white">{skill.version}</p>
            </div>
            <div className="rounded-xl border border-gray-200 px-4 py-3 dark:border-gray-700">
              <p className="text-xs text-gray-500">状态</p>
              <p className="mt-1 font-medium text-gray-900 dark:text-white">{skill.status}</p>
            </div>
            <div className="rounded-xl border border-gray-200 px-4 py-3 dark:border-gray-700">
              <p className="text-xs text-gray-500">来源</p>
              <p className="mt-1 font-medium text-gray-900 dark:text-white">{skill.source_type}</p>
            </div>
            <div className="rounded-xl border border-gray-200 px-4 py-3 dark:border-gray-700">
              <p className="text-xs text-gray-500">已绑定机器人</p>
              <p className="mt-1 font-medium text-gray-900 dark:text-white">{skill.bound_robot_count}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.3fr_1fr]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>README / 说明</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="whitespace-pre-wrap rounded-xl bg-gray-50 p-4 text-sm leading-6 text-gray-700 dark:bg-gray-900/50 dark:text-gray-200">
                {skill.readme_content || '暂无 README 内容'}
              </pre>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileCode2 className="h-5 w-5 text-primary-600" />
                Prompt Entrypoints
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {skill.prompts.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">当前 skill 没有暴露 prompt 入口文件。</p>
              ) : (
                skill.prompts.map((prompt) => (
                  <div key={prompt.key} className="rounded-xl border border-gray-200 dark:border-gray-700">
                    <div className="border-b border-gray-200 px-4 py-3 dark:border-gray-700">
                      <p className="text-sm font-semibold text-gray-900 dark:text-white">{prompt.key}</p>
                      <p className="mt-1 text-xs text-gray-500">{prompt.path}</p>
                    </div>
                    <pre className="whitespace-pre-wrap px-4 py-4 text-sm leading-6 text-gray-700 dark:text-gray-200">
                      {prompt.content}
                    </pre>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Manifest 摘要</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="max-h-[420px] overflow-auto rounded-xl bg-gray-50 p-4 text-xs leading-6 text-gray-700 dark:bg-gray-900/50 dark:text-gray-200">
                {JSON.stringify(skill.manifest, null, 2)}
              </pre>
              <div className="mt-4 space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <p>安装路径：{skill.install_path}</p>
                <p>安装时间：{skill.installed_at ? formatDateTime(skill.installed_at) : '未知'}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Link2 className="h-5 w-5 text-primary-600" />
                绑定机器人
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {skill.bound_robots.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">当前还没有机器人绑定这个 skill。</p>
              ) : (
                skill.bound_robots.map((binding) => (
                  <div key={`${binding.robot_id}-${binding.skill_slug}`} className="rounded-xl border border-gray-200 px-4 py-3 dark:border-gray-700">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">{binding.robot_name || `机器人 #${binding.robot_id}`}</p>
                        <p className="mt-1 text-xs text-gray-500">
                          版本 {binding.skill_version} · priority {binding.priority} · {binding.status}
                        </p>
                      </div>
                      <Link
                        href={`/robots/${binding.robot_id}/edit-test`}
                        className="text-sm text-primary-600 transition-colors hover:text-primary-700"
                      >
                        查看机器人
                      </Link>
                    </div>
                    {Object.keys(binding.binding_config || {}).length > 0 && (
                      <pre className="mt-3 rounded-lg bg-gray-50 p-3 text-xs text-gray-700 dark:bg-gray-900/50 dark:text-gray-200">
                        {JSON.stringify(binding.binding_config, null, 2)}
                      </pre>
                    )}
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
