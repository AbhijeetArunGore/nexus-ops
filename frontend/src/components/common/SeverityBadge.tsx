import React from 'react';
import { Severity } from '../../types';

interface Props {
  severity: Severity;
  size?: 'sm' | 'md' | 'lg';
}

export const SeverityBadge: React.FC<Props> = ({ severity, size = 'md' }) => {
  const styles: Record<Severity, string> = {
    CRITICAL: 'bg-red-950/80 text-red-400 border-red-800/60 animate-pulse',
    HIGH: 'bg-orange-950/80 text-orange-400 border-orange-800/60',
    MEDIUM: 'bg-yellow-950/80 text-yellow-400 border-yellow-800/60',
    LOW: 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60'
  };

  const sizeClasses = {
    sm: 'text-[10px] px-1.5 py-0.5',
    md: 'text-xs px-2.5 py-1',
    lg: 'text-sm px-3 py-1.5'
  };

  return (
    <span className={`inline-flex items-center font-mono font-semibold uppercase tracking-wider rounded border ${styles[severity]} ${sizeClasses[size]}`}>
      <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
        severity === 'CRITICAL' ? 'bg-red-400' :
        severity === 'HIGH' ? 'bg-orange-400' :
        severity === 'MEDIUM' ? 'bg-yellow-400' : 'bg-emerald-400'
      }`} />
      {severity}
    </span>
  );
};
