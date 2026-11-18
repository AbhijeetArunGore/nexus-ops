import React from 'react';
import { CustomerImpact } from '../../types';

interface Props {
  impact: CustomerImpact;
}

export const ImpactBadge: React.FC<Props> = ({ impact }) => {
  const styles: Record<CustomerImpact, string> = {
    CONFIRMED: 'bg-red-900/40 text-red-300 border-red-700/50',
    SUSPECTED: 'bg-amber-900/40 text-amber-300 border-amber-700/50',
    UNKNOWN: 'bg-gray-800/60 text-gray-400 border-gray-700/50'
  };

  return (
    <span className={`inline-flex items-center text-[11px] font-mono px-2 py-0.5 rounded border ${styles[impact]}`}>
      Impact: {impact}
    </span>
  );
};
