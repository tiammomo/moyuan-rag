import apiClient from '@/lib/api-client';
import type {
  SkillBinding,
  SkillBindingCreate,
  SkillBindingUpdate,
  SkillDetail,
  SkillInstallResponse,
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
