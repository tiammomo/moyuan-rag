import apiClient from '@/lib/api-client';
import type {
  SkillAuditLogListResponse,
  SkillBinding,
  SkillBindingCreate,
  SkillBindingUpdate,
  SkillDetail,
  SkillInstallResponse,
  SkillRemoteInstallRequest,
  SkillRemoteInstallResponse,
  SkillInstallTask,
  SkillInstallTaskActionResponse,
  SkillInstallTaskListResponse,
  SkillListResponse,
} from '@/types';

export const skillApi = {
  getList: async (): Promise<SkillListResponse> => {
    const response = await apiClient.get<SkillListResponse>('/skills');
    return response.data;
  },

  getBySlug: async (slug: string): Promise<SkillDetail> => {
    const response = await apiClient.get<SkillDetail>(`/skills/${slug}`);
    return response.data;
  },

  installLocal: async (file: File): Promise<SkillInstallResponse> => {
    const formData = new FormData();
    formData.append('package', file);
    const response = await apiClient.post<SkillInstallResponse>('/skills/install-local', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  installRemote: async (payload: SkillRemoteInstallRequest): Promise<SkillRemoteInstallResponse> => {
    const response = await apiClient.post<SkillRemoteInstallResponse>('/skills/install-remote', payload);
    return response.data;
  },

  getInstallTasks: async (params?: {
    skip?: number;
    limit?: number;
    status_filter?: string;
    source_type?: string;
    skill_slug?: string;
    requested_by_username?: string;
  }): Promise<SkillInstallTaskListResponse> => {
    const response = await apiClient.get<SkillInstallTaskListResponse>('/skills/install-tasks', { params });
    return response.data;
  },

  getInstallTaskById: async (taskId: number): Promise<SkillInstallTask> => {
    const response = await apiClient.get<SkillInstallTask>(`/skills/install-tasks/${taskId}`);
    return response.data;
  },

  retryInstallTask: async (taskId: number): Promise<SkillInstallTaskActionResponse> => {
    const response = await apiClient.post<SkillInstallTaskActionResponse>(`/skills/install-tasks/${taskId}/retry`);
    return response.data;
  },

  cancelInstallTask: async (taskId: number): Promise<SkillInstallTaskActionResponse> => {
    const response = await apiClient.post<SkillInstallTaskActionResponse>(`/skills/install-tasks/${taskId}/cancel`);
    return response.data;
  },

  getAuditLogs: async (params?: {
    skip?: number;
    limit?: number;
    action_filter?: string;
    status_filter?: string;
    actor_username?: string;
    skill_slug?: string;
    robot_id?: number;
    install_task_id?: number;
  }): Promise<SkillAuditLogListResponse> => {
    const response = await apiClient.get<SkillAuditLogListResponse>('/skills/audit-logs', { params });
    return response.data;
  },

  getRobotBindings: async (robotId: number): Promise<SkillBinding[]> => {
    const response = await apiClient.get<SkillBinding[]>(`/robots/${robotId}/skills`);
    return response.data;
  },

  bindToRobot: async (robotId: number, slug: string, payload: SkillBindingCreate = {}): Promise<SkillBinding> => {
    const response = await apiClient.post<SkillBinding>(`/robots/${robotId}/skills/${slug}`, payload);
    return response.data;
  },

  updateRobotBinding: async (robotId: number, slug: string, payload: SkillBindingUpdate): Promise<SkillBinding> => {
    const response = await apiClient.put<SkillBinding>(`/robots/${robotId}/skills/${slug}`, payload);
    return response.data;
  },

  removeFromRobot: async (robotId: number, slug: string): Promise<{ message: string }> => {
    const response = await apiClient.delete<{ message: string }>(`/robots/${robotId}/skills/${slug}`);
    return response.data;
  },
};
