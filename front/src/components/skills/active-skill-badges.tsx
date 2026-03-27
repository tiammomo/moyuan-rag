'use client';

import type { SkillBinding } from '@/types';

import { cn } from '@/lib/utils';

interface ActiveSkillBadgesProps {
  skills: SkillBinding[];
  emptyLabel?: string;
  className?: string;
}

export function ActiveSkillBadges({
  skills,
  emptyLabel = '当前未启用技能',
  className,
}: ActiveSkillBadgesProps) {
  if (!skills.length) {
    return <p className={cn('text-xs text-gray-500 dark:text-gray-400', className)}>{emptyLabel}</p>;
  }

  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {skills.map((skill) => (
        <span
          key={`${skill.robot_id}-${skill.skill_slug}`}
          className="inline-flex items-center gap-1 rounded-full border border-primary-200 bg-primary-50 px-2.5 py-1 text-xs text-primary-700 dark:border-primary-800 dark:bg-primary-950/40 dark:text-primary-300"
          title={skill.skill_description || skill.skill_slug}
        >
          <span className="font-medium">{skill.skill_name || skill.skill_slug}</span>
          <span className="text-[11px] opacity-80">P{skill.priority}</span>
        </span>
      ))}
    </div>
  );
}
