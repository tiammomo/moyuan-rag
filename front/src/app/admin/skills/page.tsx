'use client';

import { useEffect, useMemo, useState, type ReactNode } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ArrowRightLeft,
  ChevronRight,
  ExternalLink,
  FileJson,
  Filter,
  GitCompare,
  History,
  ListChecks,
  RefreshCcw,
  ShieldCheck,
  Siren,
  X,
} from 'lucide-react';
import toast from 'react-hot-toast';

import { robotApi, skillApi } from '@/api';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Input,
  Modal,
  PageLoading,
  Select,
} from '@/components/ui';
import { formatDateTime } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth-store';
import type {
  RobotBrief,
  SkillAuditLog,
  SkillBinding,
  SkillDetail,
  SkillInstallTask,
  SkillInstalledVariant,
  SkillListItem,
} from '@/types';

const taskStatusOptions = [
  { value: '', label: '全部状态' },
  { value: 'pending', label: 'pending' },
  { value: 'extracting', label: 'extracting' },
  { value: 'installed', label: 'installed' },
  { value: 'failed', label: 'failed' },
  { value: 'rejected', label: 'rejected' },
  { value: 'verifying', label: 'verifying' },
];

const taskSourceOptions = [
  { value: '', label: '全部来源' },
  { value: 'local', label: 'local' },
  { value: 'remote', label: 'remote' },
];

const auditActionOptions = [
  { value: '', label: '全部动作' },
  { value: 'skill.install_local', label: 'skill.install_local' },
  { value: 'skill.install_remote', label: 'skill.install_remote' },
  { value: 'skill.bind', label: 'skill.bind' },
  { value: 'skill.update_binding', label: 'skill.update_binding' },
  { value: 'skill.unbind', label: 'skill.unbind' },
];

const auditStatusOptions = [
  { value: '', label: '全部状态' },
  { value: 'success', label: 'success' },
  { value: 'failed', label: 'failed' },
  { value: 'rejected', label: 'rejected' },
];

function formatJson(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

function StatusBadge({
  value,
  palette = 'slate',
}: {
  value: string;
  palette?: 'slate' | 'success' | 'warning' | 'danger' | 'primary';
}) {
  const paletteClass = {
    slate: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200',
    success: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
    warning: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
    danger: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    primary: 'bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300',
  };

  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${paletteClass[palette]}`}>
      {value}
    </span>
  );
}

function JsonDrawer({
  open,
  title,
  subtitle,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="absolute inset-y-0 right-0 flex w-full justify-end">
        <div className="h-full w-full max-w-2xl overflow-y-auto border-l border-gray-200 bg-white shadow-2xl dark:border-gray-700 dark:bg-gray-900">
          <div className="sticky top-0 z-10 flex items-start justify-between border-b border-gray-200 bg-white px-6 py-4 dark:border-gray-700 dark:bg-gray-900">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h2>
              {subtitle ? <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{subtitle}</p> : null}
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-2 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-300"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className="space-y-6 px-6 py-6">{children}</div>
        </div>
      </div>
    </div>
  );
}

function SummaryCard({
  title,
  value,
  description,
  icon,
}: {
  title: string;
  value: string | number;
  description: string;
  icon: ReactNode;
}) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-4 p-5">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
          <p className="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">{value}</p>
          <p className="mt-2 text-xs leading-5 text-gray-500 dark:text-gray-400">{description}</p>
        </div>
        <div className="rounded-2xl bg-primary-50 p-3 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
          {icon}
        </div>
      </CardContent>
    </Card>
  );
}

export default function AdminSkillsPage() {
  const router = useRouter();
  const { user } = useAuthStore();

  const [skills, setSkills] = useState<SkillListItem[]>([]);
  const [robotOptions, setRobotOptions] = useState<RobotBrief[]>([]);
  const [selectedSkillSlug, setSelectedSkillSlug] = useState('');
  const [selectedSkill, setSelectedSkill] = useState<SkillDetail | null>(null);
  const [installTasks, setInstallTasks] = useState<SkillInstallTask[]>([]);
  const [auditLogs, setAuditLogs] = useState<SkillAuditLog[]>([]);
  const [taskTotal, setTaskTotal] = useState(0);
  const [auditTotal, setAuditTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [operationKey, setOperationKey] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<SkillInstallTask | null>(null);
  const [selectedLog, setSelectedLog] = useState<SkillAuditLog | null>(null);
  const [rollbackVariant, setRollbackVariant] = useState<SkillInstalledVariant | null>(null);

  const [taskFilters, setTaskFilters] = useState({
    status_filter: '',
    source_type: '',
    skill_slug: '',
    requested_by_username: '',
  });
  const [auditFilters, setAuditFilters] = useState({
    action_filter: '',
    status_filter: '',
    actor_username: '',
    skill_slug: '',
    robot_id: '',
  });

  const currentVersion = selectedSkill?.version ?? '';
  const driftedBindings = useMemo(
    () => (selectedSkill?.bound_robots ?? []).filter((binding) => binding.skill_version !== currentVersion),
    [currentVersion, selectedSkill],
  );
  const failedTaskCount = useMemo(
    () => installTasks.filter((task) => task.status === 'failed' || task.status === 'rejected').length,
    [installTasks],
  );

  const rollbackImpact = useMemo(() => {
    if (!selectedSkill || !rollbackVariant) {
      return { alreadyPinned: [], currentBindings: [] as SkillBinding[] };
    }

    return {
      alreadyPinned: selectedSkill.bound_robots.filter((binding) => binding.skill_version === rollbackVariant.version),
      currentBindings: selectedSkill.bound_robots.filter((binding) => binding.skill_version === selectedSkill.version),
    };
  }, [rollbackVariant, selectedSkill]);

  const loadConsole = async (showLoading = true) => {
    if (showLoading) {
      setLoading(true);
    } else {
      setRefreshing(true);
    }

    try {
      const [skillsResponse, taskResponse, auditResponse, robotResponse] = await Promise.all([
        skillApi.getList(),
        skillApi.getInstallTasks({
          limit: 50,
          status_filter: taskFilters.status_filter || undefined,
          source_type: taskFilters.source_type || undefined,
          skill_slug: taskFilters.skill_slug || undefined,
          requested_by_username: taskFilters.requested_by_username.trim() || undefined,
        }),
        skillApi.getAuditLogs({
          limit: 50,
          action_filter: auditFilters.action_filter || undefined,
          status_filter: auditFilters.status_filter || undefined,
          actor_username: auditFilters.actor_username.trim() || undefined,
          skill_slug: auditFilters.skill_slug || undefined,
          robot_id: auditFilters.robot_id ? Number(auditFilters.robot_id) : undefined,
        }),
        robotApi.getBriefList(),
      ]);

      setSkills(skillsResponse.items);
      setInstallTasks(taskResponse.items);
      setTaskTotal(taskResponse.total);
      setAuditLogs(auditResponse.items);
      setAuditTotal(auditResponse.total);
      setRobotOptions(robotResponse);

      setSelectedSkillSlug((current) => {
        if (current && skillsResponse.items.some((skill) => skill.slug === current)) {
          return current;
        }
        return skillsResponse.items[0]?.slug ?? '';
      });
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '加载 skills 治理数据失败');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const loadSkillDetail = async (skillSlug: string) => {
    setDetailLoading(true);
    try {
      const detail = await skillApi.getBySlug(skillSlug);
      setSelectedSkill(detail);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '加载 skill 详情失败');
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role === 'admin') {
      void loadConsole(true);
      return;
    }
    if (user?.role === 'user') {
      router.push('/chat');
    }
  }, [
    auditFilters.action_filter,
    auditFilters.actor_username,
    auditFilters.robot_id,
    auditFilters.skill_slug,
    auditFilters.status_filter,
    router,
    taskFilters.requested_by_username,
    taskFilters.skill_slug,
    taskFilters.source_type,
    taskFilters.status_filter,
    user,
  ]);

  useEffect(() => {
    if (user?.role === 'admin' && selectedSkillSlug) {
      void loadSkillDetail(selectedSkillSlug);
    }
  }, [selectedSkillSlug, user]);

  const refreshAll = async () => {
    await loadConsole(false);
    if (selectedSkillSlug) {
      await loadSkillDetail(selectedSkillSlug);
    }
  };

  const handleRebind = async (binding: SkillBinding) => {
    const key = `${binding.robot_id}:${binding.skill_slug}`;
    setOperationKey(key);
    try {
      await skillApi.bindToRobot(binding.robot_id, binding.skill_slug, {
        priority: binding.priority,
        status: binding.status,
        binding_config: binding.binding_config,
      });
      toast.success(`已将机器人 ${binding.robot_name || binding.robot_id} 回绑到当前版本`);
      await refreshAll();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '回绑失败');
    } finally {
      setOperationKey(null);
    }
  };

  const handleRebindAll = async () => {
    if (!driftedBindings.length) {
      return;
    }

    setOperationKey('rebind-all');
    try {
      for (const binding of driftedBindings) {
        await skillApi.bindToRobot(binding.robot_id, binding.skill_slug, {
          priority: binding.priority,
          status: binding.status,
          binding_config: binding.binding_config,
        });
      }
      toast.success(`已完成 ${driftedBindings.length} 条漂移绑定回绑`);
      await refreshAll();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '批量回绑失败');
    } finally {
      setOperationKey(null);
    }
  };

  if (user?.role !== 'admin') {
    return null;
  }

  if (loading) {
    return <PageLoading text="加载 skills 治理控制台中..." />;
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-primary-200 bg-primary-50 px-3 py-1 text-xs font-medium text-primary-700 dark:border-primary-800 dark:bg-primary-900/30 dark:text-primary-300">
            <ShieldCheck className="h-3.5 w-3.5" />
            Skills Governance
          </div>
          <h1 className="mt-4 text-3xl font-bold text-gray-900 dark:text-white">Skills 管理后台</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-600 dark:text-gray-400">
            这里汇总安装任务、审计日志、版本差异和机器人绑定漂移，管理员可以在一个页面内完成排查、回绑和回滚准备。
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="outline" onClick={() => void refreshAll()} disabled={refreshing || detailLoading}>
            <RefreshCcw className={`mr-2 h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            刷新治理视图
          </Button>
          <Link href="/skills">
            <Button variant="secondary">
              <ExternalLink className="mr-2 h-4 w-4" />
              前往 Skills 列表
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          title="安装任务"
          value={taskTotal}
          description="最近 50 条任务会展示在下方，可按状态、来源和请求人过滤。"
          icon={<ListChecks className="h-5 w-5" />}
        />
        <SummaryCard
          title="失败 / 拒绝任务"
          value={failedTaskCount}
          description="失败与拒绝安装会优先暴露，帮助管理员快速定位风险来源。"
          icon={<Siren className="h-5 w-5" />}
        />
        <SummaryCard
          title="审计日志"
          value={auditTotal}
          description="覆盖本地安装、远端安装尝试、绑定、更新绑定与解绑操作。"
          icon={<FileJson className="h-5 w-5" />}
        />
        <SummaryCard
          title="版本漂移绑定"
          value={driftedBindings.length}
          description="当机器人仍绑定历史 skill 版本时，可以直接在此页面执行安全回绑。"
          icon={<GitCompare className="h-5 w-5" />}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <CardHeader className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <CardTitle>安装任务</CardTitle>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">查看本地安装和远端安装请求的执行轨迹。</p>
              </div>
              <StatusBadge value={`${taskTotal} 条`} palette="primary" />
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
              <Select
                value={taskFilters.status_filter}
                onChange={(event) => setTaskFilters((prev) => ({ ...prev, status_filter: event.target.value }))}
                options={taskStatusOptions}
              />
              <Select
                value={taskFilters.source_type}
                onChange={(event) => setTaskFilters((prev) => ({ ...prev, source_type: event.target.value }))}
                options={taskSourceOptions}
              />
              <Select
                value={taskFilters.skill_slug}
                onChange={(event) => setTaskFilters((prev) => ({ ...prev, skill_slug: event.target.value }))}
                options={[
                  { value: '', label: '全部 skill' },
                  ...skills.map((skill) => ({ value: skill.slug, label: skill.name })),
                ]}
              />
              <Input
                value={taskFilters.requested_by_username}
                onChange={(event) =>
                  setTaskFilters((prev) => ({ ...prev, requested_by_username: event.target.value }))
                }
                placeholder="请求人用户名"
              />
            </div>
            <div className="flex justify-end">
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  setTaskFilters({
                    status_filter: '',
                    source_type: '',
                    skill_slug: '',
                    requested_by_username: '',
                  })
                }
              >
                <Filter className="mr-2 h-4 w-4" />
                重置任务过滤器
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {installTasks.length === 0 ? (
              <EmptyState
                title="没有匹配的安装任务"
                description="调整过滤器后再试，或等待新的安装请求进入治理台。"
              />
            ) : (
              installTasks.map((task) => (
                <div
                  key={task.id}
                  className="rounded-2xl border border-gray-200 p-4 transition hover:border-primary-300 dark:border-gray-700 dark:hover:border-primary-700"
                >
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-gray-900 dark:text-white">
                          任务 #{task.id} · {task.installed_skill_slug || task.package_name || '未识别 skill'}
                        </p>
                        <StatusBadge
                          value={task.status}
                          palette={
                            task.status === 'installed'
                              ? 'success'
                              : task.status === 'failed' || task.status === 'rejected'
                                ? 'danger'
                                : 'warning'
                          }
                        />
                        <StatusBadge value={task.source_type} />
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        请求人 {task.requested_by_username || '未知'} · 创建于 {formatDateTime(task.created_at)}
                        {task.finished_at ? ` · 完成于 ${formatDateTime(task.finished_at)}` : ''}
                      </p>
                      {task.error_message ? (
                        <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">
                          {task.error_message}
                        </p>
                      ) : null}
                    </div>
                    <Button variant="outline" size="sm" onClick={() => setSelectedTask(task)}>
                      查看详情
                      <ChevronRight className="ml-2 h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <CardTitle>审计日志</CardTitle>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">按动作、角色和目标资源快速回溯 skills 相关操作。</p>
              </div>
              <StatusBadge value={`${auditTotal} 条`} palette="primary" />
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <Select
                value={auditFilters.action_filter}
                onChange={(event) => setAuditFilters((prev) => ({ ...prev, action_filter: event.target.value }))}
                options={auditActionOptions}
              />
              <Select
                value={auditFilters.status_filter}
                onChange={(event) => setAuditFilters((prev) => ({ ...prev, status_filter: event.target.value }))}
                options={auditStatusOptions}
              />
              <Select
                value={auditFilters.skill_slug}
                onChange={(event) => setAuditFilters((prev) => ({ ...prev, skill_slug: event.target.value }))}
                options={[
                  { value: '', label: '全部 skill' },
                  ...skills.map((skill) => ({ value: skill.slug, label: skill.name })),
                ]}
              />
              <Select
                value={auditFilters.robot_id}
                onChange={(event) => setAuditFilters((prev) => ({ ...prev, robot_id: event.target.value }))}
                options={[
                  { value: '', label: '全部机器人' },
                  ...robotOptions.map((robot) => ({ value: robot.id, label: `${robot.name} (#${robot.id})` })),
                ]}
              />
              <div className="md:col-span-2">
                <Input
                  value={auditFilters.actor_username}
                  onChange={(event) => setAuditFilters((prev) => ({ ...prev, actor_username: event.target.value }))}
                  placeholder="操作人用户名"
                />
              </div>
            </div>
            <div className="flex justify-end">
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  setAuditFilters({
                    action_filter: '',
                    status_filter: '',
                    actor_username: '',
                    skill_slug: '',
                    robot_id: '',
                  })
                }
              >
                <Filter className="mr-2 h-4 w-4" />
                重置审计过滤器
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {auditLogs.length === 0 ? (
              <EmptyState title="没有匹配的审计日志" description="当前过滤条件下没有找到相关记录。" />
            ) : (
              auditLogs.map((log) => (
                <div
                  key={log.id}
                  className="rounded-2xl border border-gray-200 p-4 transition hover:border-primary-300 dark:border-gray-700 dark:hover:border-primary-700"
                >
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-gray-900 dark:text-white">{log.action}</p>
                        <StatusBadge
                          value={log.status}
                          palette={
                            log.status === 'success'
                              ? 'success'
                              : log.status === 'failed' || log.status === 'rejected'
                                ? 'danger'
                                : 'warning'
                          }
                        />
                        {log.skill_slug ? <StatusBadge value={log.skill_slug} /> : null}
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {log.actor_username || '未知操作人'} · {log.actor_role || 'unknown'} · {formatDateTime(log.created_at)}
                      </p>
                      {log.message ? (
                        <p className="text-sm leading-6 text-gray-700 dark:text-gray-300">{log.message}</p>
                      ) : null}
                    </div>
                    <Button variant="outline" size="sm" onClick={() => setSelectedLog(log)}>
                      查看详情
                      <ChevronRight className="ml-2 h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[0.72fr_1.28fr]">
        <Card>
          <CardHeader className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <CardTitle>版本对比</CardTitle>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">对照当前 registry 版本与历史安装版本，查看哪些机器人仍绑定旧版本。</p>
              </div>
              {detailLoading ? <StatusBadge value="加载中" palette="warning" /> : null}
            </div>
            <Select
              value={selectedSkillSlug}
              onChange={(event) => setSelectedSkillSlug(event.target.value)}
              options={skills.map((skill) => ({
                value: skill.slug,
                label: `${skill.name} (${skill.version})`,
              }))}
            />
          </CardHeader>
          <CardContent className="space-y-4">
            {selectedSkill ? (
              <>
                <div className="rounded-2xl border border-gray-200 bg-gray-50/80 p-4 dark:border-gray-700 dark:bg-gray-900/40">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-lg font-semibold text-gray-900 dark:text-white">{selectedSkill.name}</p>
                      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{selectedSkill.slug}</p>
                    </div>
                    <StatusBadge value={`当前版本 ${selectedSkill.version}`} palette="primary" />
                  </div>
                  <p className="mt-3 text-sm leading-6 text-gray-600 dark:text-gray-400">
                    {selectedSkill.description || '暂无描述。'}
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {selectedSkill.prompts.map((prompt) => (
                      <StatusBadge key={prompt.key} value={prompt.key} />
                    ))}
                  </div>
                </div>

                <div className="space-y-3">
                  {selectedSkill.installed_variants.map((variant) => (
                    <div
                      key={`${selectedSkill.slug}-${variant.version}`}
                      className="rounded-2xl border border-gray-200 p-4 dark:border-gray-700"
                    >
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="text-sm font-semibold text-gray-900 dark:text-white">{variant.version}</p>
                            {variant.is_current ? (
                              <StatusBadge value="registry 当前版本" palette="success" />
                            ) : (
                              <StatusBadge value="历史安装版本" palette="warning" />
                            )}
                          </div>
                          <p className="mt-2 text-xs leading-5 text-gray-500 dark:text-gray-400">
                            安装路径 {variant.install_path}
                            {variant.installed_at ? ` · 当前记录安装于 ${formatDateTime(variant.installed_at)}` : ''}
                          </p>
                          <div className="mt-3 flex flex-wrap gap-2">
                            {variant.prompt_keys.length ? (
                              variant.prompt_keys.map((promptKey) => <StatusBadge key={promptKey} value={promptKey} />)
                            ) : (
                              <StatusBadge value="无 prompt entrypoint" />
                            )}
                          </div>
                        </div>
                        <div className="flex flex-col items-start gap-2 lg:items-end">
                          <StatusBadge value={`绑定机器人 ${variant.bound_robot_count}`} palette="primary" />
                          {!variant.is_current ? (
                            <Button variant="outline" size="sm" onClick={() => setRollbackVariant(variant)}>
                              <History className="mr-2 h-4 w-4" />
                              准备回滚
                            </Button>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <EmptyState title="没有可分析的 skill" description="请先安装至少一个本地 skill，再进入治理台。" />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="space-y-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <CardTitle>机器人绑定与版本漂移</CardTitle>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">优先处理仍绑定旧版本的机器人，确保运行时 prompt 与当前 registry 对齐。</p>
              </div>
              {driftedBindings.length ? (
                <Button size="sm" onClick={() => void handleRebindAll()} loading={operationKey === 'rebind-all'}>
                  <ArrowRightLeft className="mr-2 h-4 w-4" />
                  批量回绑到当前版本
                </Button>
              ) : (
                <StatusBadge value="无版本漂移" palette="success" />
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {!selectedSkill ? (
              <EmptyState title="请选择一个 skill" description="从左侧选择 skill 后，这里会展示绑定与漂移信息。" />
            ) : selectedSkill.bound_robots.length === 0 ? (
              <EmptyState title="当前 skill 没有关联机器人" description="可以先在机器人编辑页绑定该 skill。" />
            ) : (
              selectedSkill.bound_robots.map((binding) => {
                const isDrifted = binding.skill_version !== selectedSkill.version;
                const actionKey = `${binding.robot_id}:${binding.skill_slug}`;
                return (
                  <div
                    key={`${binding.robot_id}-${binding.skill_slug}`}
                    className="rounded-2xl border border-gray-200 p-4 dark:border-gray-700"
                  >
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-sm font-semibold text-gray-900 dark:text-white">
                            {binding.robot_name || `机器人 #${binding.robot_id}`}
                          </p>
                          <StatusBadge value={`当前绑定 ${binding.skill_version}`} palette={isDrifted ? 'warning' : 'success'} />
                          <StatusBadge value={binding.status} />
                          <StatusBadge value={`优先级 ${binding.priority}`} />
                        </div>
                        {binding.skill_description ? (
                          <p className="text-sm leading-6 text-gray-600 dark:text-gray-400">{binding.skill_description}</p>
                        ) : null}
                        <div className="flex flex-wrap gap-2">
                          {binding.prompt_keys.map((promptKey) => (
                            <StatusBadge key={`${binding.robot_id}-${promptKey}`} value={promptKey} />
                          ))}
                        </div>
                        <div className="flex flex-wrap gap-3 text-xs text-gray-500 dark:text-gray-400">
                          <span>创建于 {formatDateTime(binding.created_at)}</span>
                          <span>更新于 {formatDateTime(binding.updated_at)}</span>
                          <Link
                            href={`/robots/${binding.robot_id}/edit-test`}
                            className="inline-flex items-center text-primary-600 hover:text-primary-700 dark:text-primary-400"
                          >
                            前往机器人编辑
                            <ExternalLink className="ml-1 h-3.5 w-3.5" />
                          </Link>
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        {isDrifted ? (
                          <Button
                            size="sm"
                            onClick={() => void handleRebind(binding)}
                            loading={operationKey === actionKey}
                          >
                            <ArrowRightLeft className="mr-2 h-4 w-4" />
                            回绑到 {selectedSkill.version}
                          </Button>
                        ) : null}
                        <Link href={`/skills/${selectedSkill.slug}`}>
                          <Button variant="outline" size="sm">
                            查看 skill 详情
                            <ExternalLink className="ml-2 h-4 w-4" />
                          </Button>
                        </Link>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>
      </div>

      <JsonDrawer
        open={selectedTask !== null}
        title={selectedTask ? `安装任务 #${selectedTask.id}` : ''}
        subtitle={selectedTask ? `${selectedTask.installed_skill_slug || selectedTask.package_name || '未识别 skill'} · ${selectedTask.status}` : undefined}
        onClose={() => setSelectedTask(null)}
      >
        {selectedTask ? (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Card>
                <CardContent className="space-y-2 p-4 text-sm text-gray-600 dark:text-gray-300">
                  <p><span className="font-medium text-gray-900 dark:text-white">来源:</span> {selectedTask.source_type}</p>
                  <p><span className="font-medium text-gray-900 dark:text-white">请求人:</span> {selectedTask.requested_by_username || '未知'}</p>
                  <p><span className="font-medium text-gray-900 dark:text-white">checksum:</span> {selectedTask.package_checksum || '未提供'}</p>
                  <p><span className="font-medium text-gray-900 dark:text-white">签名算法:</span> {selectedTask.signature_algorithm || '未提供'}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="space-y-2 p-4 text-sm text-gray-600 dark:text-gray-300">
                  <p><span className="font-medium text-gray-900 dark:text-white">创建时间:</span> {formatDateTime(selectedTask.created_at)}</p>
                  <p><span className="font-medium text-gray-900 dark:text-white">更新时间:</span> {formatDateTime(selectedTask.updated_at)}</p>
                  <p><span className="font-medium text-gray-900 dark:text-white">完成时间:</span> {selectedTask.finished_at ? formatDateTime(selectedTask.finished_at) : '未完成'}</p>
                  <p><span className="font-medium text-gray-900 dark:text-white">安装版本:</span> {selectedTask.installed_skill_version || '未知'}</p>
                </CardContent>
              </Card>
            </div>

            {selectedTask.error_message ? (
              <div className="rounded-2xl bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">
                {selectedTask.error_message}
              </div>
            ) : null}

            <Card>
              <CardHeader>
                <CardTitle className="text-base">任务详情 JSON</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <pre className="max-h-[420px] overflow-auto rounded-b-lg bg-gray-950 px-4 py-4 text-xs leading-6 text-gray-100">
                  {formatJson(selectedTask.details)}
                </pre>
              </CardContent>
            </Card>
          </>
        ) : null}
      </JsonDrawer>

      <JsonDrawer
        open={selectedLog !== null}
        title={selectedLog ? `审计日志 #${selectedLog.id}` : ''}
        subtitle={selectedLog ? `${selectedLog.action} · ${selectedLog.status}` : undefined}
        onClose={() => setSelectedLog(null)}
      >
        {selectedLog ? (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Card>
                <CardContent className="space-y-2 p-4 text-sm text-gray-600 dark:text-gray-300">
                  <p><span className="font-medium text-gray-900 dark:text-white">操作人:</span> {selectedLog.actor_username || '未知'}</p>
                  <p><span className="font-medium text-gray-900 dark:text-white">角色:</span> {selectedLog.actor_role || 'unknown'}</p>
                  <p><span className="font-medium text-gray-900 dark:text-white">skill:</span> {selectedLog.skill_slug || '未关联'}</p>
                  <p><span className="font-medium text-gray-900 dark:text-white">robot_id:</span> {selectedLog.robot_id ?? '未关联'}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="space-y-2 p-4 text-sm text-gray-600 dark:text-gray-300">
                  <p><span className="font-medium text-gray-900 dark:text-white">资源类型:</span> {selectedLog.target_type}</p>
                  <p><span className="font-medium text-gray-900 dark:text-white">安装任务:</span> {selectedLog.install_task_id ?? '无'}</p>
                  <p><span className="font-medium text-gray-900 dark:text-white">skill 版本:</span> {selectedLog.skill_version || '未知'}</p>
                  <p><span className="font-medium text-gray-900 dark:text-white">时间:</span> {formatDateTime(selectedLog.created_at)}</p>
                </CardContent>
              </Card>
            </div>

            {selectedLog.message ? (
              <div className="rounded-2xl bg-blue-50 p-4 text-sm text-blue-700 dark:bg-blue-900/20 dark:text-blue-300">
                {selectedLog.message}
              </div>
            ) : null}

            <Card>
              <CardHeader>
                <CardTitle className="text-base">审计详情 JSON</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <pre className="max-h-[420px] overflow-auto rounded-b-lg bg-gray-950 px-4 py-4 text-xs leading-6 text-gray-100">
                  {formatJson(selectedLog.details)}
                </pre>
              </CardContent>
            </Card>
          </>
        ) : null}
      </JsonDrawer>

      <Modal
        isOpen={rollbackVariant !== null}
        onClose={() => setRollbackVariant(null)}
        title={rollbackVariant ? `回滚准备：${rollbackVariant.version}` : '回滚准备'}
        size="4xl"
      >
        {rollbackVariant && selectedSkill ? (
          <div className="space-y-6">
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-100">
              当前页面只提供回滚准备信息，不会直接切换 registry 当前版本。建议管理员先确认目标版本、影响机器人与回绑路径，再执行受控发布。
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <Card>
                <CardContent className="p-4">
                  <p className="text-sm text-gray-500 dark:text-gray-400">当前 registry 版本</p>
                  <p className="mt-2 text-xl font-semibold text-gray-900 dark:text-white">{selectedSkill.version}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <p className="text-sm text-gray-500 dark:text-gray-400">回滚目标版本</p>
                  <p className="mt-2 text-xl font-semibold text-gray-900 dark:text-white">{rollbackVariant.version}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <p className="text-sm text-gray-500 dark:text-gray-400">已在目标版本上的机器人</p>
                  <p className="mt-2 text-xl font-semibold text-gray-900 dark:text-white">{rollbackImpact.alreadyPinned.length}</p>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">建议操作顺序</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm leading-6 text-gray-600 dark:text-gray-300">
                <p>1. 确认目标版本 `{rollbackVariant.version}` 的 prompt entrypoint 与当前机器人需求一致。</p>
                <p>2. 导出当前仍绑定 `{selectedSkill.version}` 的机器人清单，作为回滚前基线。</p>
                <p>3. 先在低风险机器人上手动改绑验证，再评估是否需要批量切换。</p>
                <p>4. 如果要正式回滚 registry 当前版本，请同步更新 skill registry、变更说明和相关截图文档。</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">受影响机器人</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {rollbackImpact.currentBindings.length === 0 ? (
                  <EmptyState title="没有机器人绑定当前版本" description="当前无需为该 skill 执行回滚切换。" />
                ) : (
                  rollbackImpact.currentBindings.map((binding) => (
                    <div
                      key={`rollback-${binding.robot_id}`}
                      className="flex flex-col gap-2 rounded-2xl border border-gray-200 p-4 dark:border-gray-700"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-gray-900 dark:text-white">
                          {binding.robot_name || `机器人 #${binding.robot_id}`}
                        </p>
                        <StatusBadge value={`当前绑定 ${binding.skill_version}`} palette="warning" />
                        <StatusBadge value={binding.status} />
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        回滚后目标版本为 {rollbackVariant.version}，建议先在机器人编辑页确认运行效果。
                      </p>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            <div className="flex justify-end">
              <Button variant="outline" onClick={() => setRollbackVariant(null)}>
                关闭
              </Button>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
