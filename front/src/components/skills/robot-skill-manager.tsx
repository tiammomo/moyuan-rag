'use client';

import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Loader2, Plug, RefreshCcw, Unplug } from 'lucide-react';
import toast from 'react-hot-toast';

import { skillApi } from '@/api';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import type { SkillBinding, SkillBindingUpdate, SkillListItem } from '@/types';

import { ActiveSkillBadges } from './active-skill-badges';

interface RobotSkillManagerProps {
  robotId: number;
}

type BindingDraftMap = Record<string, { priority: number; status: string }>;

function buildDrafts(bindings: SkillBinding[]): BindingDraftMap {
  return bindings.reduce<BindingDraftMap>((acc, binding) => {
    acc[binding.skill_slug] = {
      priority: binding.priority,
      status: binding.status,
    };
    return acc;
  }, {});
}

export function RobotSkillManager({ robotId }: RobotSkillManagerProps) {
  const searchParams = useSearchParams();
  const [installedSkills, setInstalledSkills] = useState<SkillListItem[]>([]);
  const [bindings, setBindings] = useState<SkillBinding[]>([]);
  const [drafts, setDrafts] = useState<BindingDraftMap>({});
  const [loading, setLoading] = useState(true);
  const [busySlug, setBusySlug] = useState<string | null>(null);

  const loadSkillState = async () => {
    setLoading(true);
    try {
      const [listResponse, bindingResponse] = await Promise.all([
        skillApi.getList(),
        skillApi.getRobotBindings(robotId),
      ]);
      const activeBindings = [...bindingResponse].sort((a, b) => a.priority - b.priority);
      setInstalledSkills(listResponse.items);
      setBindings(activeBindings);
      setDrafts(buildDrafts(activeBindings));
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || '加载技能信息失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadSkillState();
  }, [robotId]);

  const boundSlugSet = useMemo(() => new Set(bindings.map((binding) => binding.skill_slug)), [bindings]);
  const activeBindings = useMemo(
    () => bindings.filter((binding) => binding.status === 'active'),
    [bindings],
  );
  const provenanceInstallTaskId = useMemo(() => {
    const rawTaskId = searchParams.get('install_task_id');
    if (!rawTaskId) {
      return undefined;
    }
    const parsedTaskId = Number.parseInt(rawTaskId, 10);
    return Number.isInteger(parsedTaskId) && parsedTaskId > 0 ? parsedTaskId : undefined;
  }, [searchParams]);
  const provenanceSkillSlug = useMemo(() => searchParams.get('skill_slug') || '', [searchParams]);
  const shouldAttachProvenance = (slug: string) =>
    Boolean(provenanceInstallTaskId && (!provenanceSkillSlug || provenanceSkillSlug === slug));
  const availableSkills = useMemo(
    () => installedSkills.filter((skill) => !boundSlugSet.has(skill.slug)),
    [boundSlugSet, installedSkills],
  );

  const updateDraft = (slug: string, patch: Partial<{ priority: number; status: string }>) => {
    setDrafts((prev) => ({
      ...prev,
      [slug]: {
        priority: patch.priority ?? prev[slug]?.priority ?? 100,
        status: patch.status ?? prev[slug]?.status ?? 'active',
      },
    }));
  };

  const handleBind = async (slug: string) => {
    setBusySlug(slug);
    try {
      await skillApi.bindToRobot(robotId, slug, {
        install_task_id: shouldAttachProvenance(slug) ? provenanceInstallTaskId : undefined,
      });
      await loadSkillState();
      toast.success('技能已绑定到机器人');
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || '绑定技能失败');
    } finally {
      setBusySlug(null);
    }
  };

  const handleUpdate = async (slug: string) => {
    const draft = drafts[slug];
    if (!draft) {
      return;
    }

    const payload: SkillBindingUpdate = {
      priority: Number.isFinite(draft.priority) ? draft.priority : 100,
      status: draft.status,
      install_task_id: shouldAttachProvenance(slug) ? provenanceInstallTaskId : undefined,
    };

    setBusySlug(slug);
    try {
      await skillApi.updateRobotBinding(robotId, slug, payload);
      await loadSkillState();
      toast.success('技能绑定已更新');
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || '更新技能绑定失败');
    } finally {
      setBusySlug(null);
    }
  };

  const handleRemove = async (slug: string) => {
    setBusySlug(slug);
    try {
      await skillApi.removeFromRobot(robotId, slug);
      await loadSkillState();
      toast.success('技能已解绑');
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || '解绑技能失败');
    } finally {
      setBusySlug(null);
    }
  };

  return (
    <Card>
      <CardHeader className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-lg">机器人技能</CardTitle>
          <Button variant="outline" size="sm" onClick={() => void loadSkillState()} disabled={loading}>
            {loading ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <RefreshCcw className="mr-1 h-4 w-4" />}
            刷新
          </Button>
        </div>
        <div>
          <p className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-200">当前生效</p>
          <ActiveSkillBadges skills={activeBindings} />
        </div>
        {provenanceInstallTaskId ? (
          <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-xs leading-6 text-blue-800 dark:border-blue-900/40 dark:bg-blue-900/20 dark:text-blue-100">
            当前从安装任务 #{provenanceInstallTaskId} 进入。绑定或更新匹配的 skill 时，会自动记录这次安装来源。
          </div>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-6">
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">已绑定技能</h3>
            <span className="text-xs text-gray-500 dark:text-gray-400">{bindings.length} 个</span>
          </div>
          {loading ? (
            <div className="rounded-xl border border-dashed border-gray-200 px-4 py-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
              正在加载技能绑定...
            </div>
          ) : bindings.length === 0 ? (
            <div className="rounded-xl border border-dashed border-gray-200 px-4 py-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
              当前机器人还没有绑定任何技能。
            </div>
          ) : (
            bindings.map((binding) => {
              const draft = drafts[binding.skill_slug] || {
                priority: binding.priority,
                status: binding.status,
              };
              return (
                <div
                  key={binding.skill_slug}
                  className="space-y-3 rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900/50"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-gray-900 dark:text-white">
                          {binding.skill_name || binding.skill_slug}
                        </p>
                        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-600 dark:bg-gray-800 dark:text-gray-300">
                          {binding.skill_version}
                        </span>
                        {binding.category && (
                          <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[11px] text-blue-700 dark:bg-blue-950/30 dark:text-blue-300">
                            {binding.category}
                          </span>
                        )}
                        {binding.provenance_install_task_id ? (
                          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">
                            安装任务 #{binding.provenance_install_task_id}
                          </span>
                        ) : null}
                      </div>
                      {binding.skill_description && (
                        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{binding.skill_description}</p>
                      )}
                      {!!binding.prompt_keys.length && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {binding.prompt_keys.map((key) => (
                            <span
                              key={`${binding.skill_slug}-${key}`}
                              className="rounded-full border border-gray-200 px-2 py-0.5 text-[11px] text-gray-600 dark:border-gray-700 dark:text-gray-300"
                            >
                              {key}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <span className="rounded-full border border-gray-200 px-2 py-1 text-[11px] text-gray-600 dark:border-gray-700 dark:text-gray-300">
                      {binding.status === 'active' ? '启用中' : '已停用'}
                    </span>
                  </div>

                  <div className="grid gap-3 md:grid-cols-[120px_150px_1fr]">
                    <label className="space-y-1 text-xs text-gray-500 dark:text-gray-400">
                      优先级
                      <input
                        type="number"
                        min={1}
                        max={9999}
                        value={draft.priority}
                        onChange={(event) =>
                          updateDraft(binding.skill_slug, {
                            priority: parseInt(event.target.value, 10) || binding.priority,
                          })
                        }
                        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 outline-none focus:border-primary-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                      />
                    </label>
                    <label className="space-y-1 text-xs text-gray-500 dark:text-gray-400">
                      状态
                      <select
                        value={draft.status}
                        onChange={(event) =>
                          updateDraft(binding.skill_slug, {
                            status: event.target.value,
                          })
                        }
                        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 outline-none focus:border-primary-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                      >
                        <option value="active">active</option>
                        <option value="disabled">disabled</option>
                      </select>
                    </label>
                    <div className="flex items-end justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => void handleUpdate(binding.skill_slug)}
                        disabled={busySlug === binding.skill_slug}
                      >
                        {busySlug === binding.skill_slug ? (
                          <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                        ) : (
                          <Plug className="mr-1 h-4 w-4" />
                        )}
                        更新
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => void handleRemove(binding.skill_slug)}
                        disabled={busySlug === binding.skill_slug}
                      >
                        <Unplug className="mr-1 h-4 w-4" />
                        解绑
                      </Button>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">可安装到该机器人</h3>
            <span className="text-xs text-gray-500 dark:text-gray-400">{availableSkills.length} 个</span>
          </div>
          {loading ? null : availableSkills.length === 0 ? (
            <div className="rounded-xl border border-dashed border-gray-200 px-4 py-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
              没有更多可绑定技能。
            </div>
          ) : (
            availableSkills.map((skill) => (
              <div
                key={skill.slug}
                className="flex flex-wrap items-start justify-between gap-3 rounded-2xl border border-gray-200 bg-gray-50/70 p-4 dark:border-gray-800 dark:bg-gray-900/30"
              >
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold text-gray-900 dark:text-white">{skill.name}</p>
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-600 dark:bg-gray-800 dark:text-gray-300">
                      {skill.version}
                    </span>
                  </div>
                  {skill.description && (
                    <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{skill.description}</p>
                  )}
                  {shouldAttachProvenance(skill.slug) ? (
                    <p className="mt-2 text-xs text-emerald-700 dark:text-emerald-300">
                      绑定后会关联安装任务 #{provenanceInstallTaskId}
                    </p>
                  ) : null}
                </div>
                <Button size="sm" onClick={() => void handleBind(skill.slug)} disabled={busySlug === skill.slug}>
                  {busySlug === skill.slug ? (
                    <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                  ) : (
                    <Plug className="mr-1 h-4 w-4" />
                  )}
                  绑定
                </Button>
              </div>
            ))
          )}
        </section>
      </CardContent>
    </Card>
  );
}
