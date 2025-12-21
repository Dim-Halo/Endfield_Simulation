import React from 'react';
import { TimelineEditor } from './TimelineEditor';

export const TimelineView: React.FC = () => {
  return (
    <div className="p-6 h-full overflow-y-auto">
      <TimelineEditor />
    </div>
  );
};
