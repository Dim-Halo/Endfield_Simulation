import React, { useRef, useState, useEffect } from 'react';
import { useDraggable, useDroppable, DndContext, DragEndEvent, useSensor, useSensors, PointerSensor, Modifier } from '@dnd-kit/core';
import { restrictToHorizontalAxis } from '@dnd-kit/modifiers';
import { CSS } from '@dnd-kit/utilities';
import { useSimulationStore, TimelineAction, ActionType } from '../store/useSimulationStore';
import { cn } from '../utils/cn'; 
import { Play, Pause, Square, Rewind } from 'lucide-react';
import { EditActionModal } from './EditActionModal';
import { getActionDuration } from '../utils/constants';

const ACTION_COLORS: Record<string, string> = {
  "Skill": "bg-blue-500 from-blue-500 to-blue-600 border-blue-400",
  "Ult": "bg-red-500 from-red-500 to-red-600 border-red-400",
  "QTE": "bg-yellow-500 from-yellow-500 to-yellow-600 border-yellow-400",
  "Attack": "bg-gray-400 from-gray-400 to-gray-500 border-gray-300",
  "Wait": "bg-transparent border-transparent",
};

interface ActionBlockProps {
  action: TimelineAction;
  totalDuration: number;
  charIndex: number;
  containerWidth: number;
  onDoubleClick: (action: TimelineAction) => void;
}

const ActionBlock: React.FC<ActionBlockProps> = ({ action, totalDuration, charIndex, containerWidth, onDoubleClick }) => {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `draggable-${charIndex}-${action.id}`,
    data: { action, charIndex, originalStartTime: action.startTime }
  });

  const [isHovered, setIsHovered] = useState(false);

  // Initial calculations
  const leftPct = (action.startTime / totalDuration) * 100;
  const widthPct = (action.duration / totalDuration) * 100;

  let currentStartTime = action.startTime;
  let transformX = transform?.x || 0;

  if (isDragging && containerWidth > 0) {
    const secondsPerPx = totalDuration / containerWidth;

    // Unclamped new time
    const rawNewTime = action.startTime + transformX * secondsPerPx;

    // Clamped new time
    currentStartTime = Math.max(0, Math.min(totalDuration - action.duration, rawNewTime));

    // Calculate clamped transform X
    const pixelsPerSecond = containerWidth / totalDuration;
    transformX = (currentStartTime - action.startTime) * pixelsPerSecond;
  }

  // If we are dragging, we want to visually clamp the movement.
  const transformStyle = transform ? {
    transform: `translate3d(${transformX}px, 0, 0)`,
  } : {};

  const style: React.CSSProperties = {
    left: `${leftPct}%`,
    width: `${widthPct}%`,
    ...transformStyle,
    zIndex: isDragging ? 100 : (isHovered ? 50 : 10),
    opacity: isDragging ? 0.9 : 1,
    touchAction: 'none',
  };

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onDoubleClick={(e) => {
        e.stopPropagation();
        onDoubleClick(action);
      }}
      className={cn(
        "absolute h-[80%] top-[10%] rounded-md border shadow-md text-xs font-bold text-white flex items-center justify-center cursor-move select-none transition-colors bg-gradient-to-b group/block",
        ACTION_COLORS[action.type] || "bg-gray-500",
        isDragging ? "ring-2 ring-white ring-opacity-50 scale-105 shadow-xl cursor-grabbing" : "cursor-grab"
      )}
      style={style}
    >
      <div className="overflow-hidden w-full text-center px-1">
        {widthPct > 2 && (
          <span className="truncate drop-shadow-sm pointer-events-none">{action.name}</span>
        )}
      </div>

      {(isDragging || isHovered) && (
        <div
          className="absolute -top-10 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-[10px] px-2 py-1 rounded shadow-lg whitespace-nowrap z-[9999] pointer-events-none font-mono flex flex-col items-center"
          style={{ minWidth: '40px' }}
        >
          <span>{currentStartTime.toFixed(2)}s</span>
          <div className="w-2 h-2 bg-gray-900 rotate-45 -mt-1 translate-y-1/2" />
        </div>
      )}
    </div>
  );
};

interface TrackProps {
  charIndex: number;
  charName: string;
  actions: TimelineAction[];
  totalDuration: number;
  trackWidth: number;
  onMouseMove: (e: React.MouseEvent, charIndex: number) => void;
  onMouseLeave: () => void;
  hoveredTime: number | null;
  isHoveredTrack: boolean;
  onActionDoubleClick: (action: TimelineAction) => void;
}

const TimelineTrack: React.FC<TrackProps> = ({ 
  charIndex, charName, actions, totalDuration, trackWidth, 
  onMouseMove, onMouseLeave, hoveredTime, isHoveredTrack, onActionDoubleClick
}) => {
  const { setNodeRef } = useDroppable({
    id: `track-${charIndex}`,
    data: { charIndex }
  });

  return (
    <div className="flex h-16 mb-2 items-center group">
      <div className="w-24 flex flex-col items-end pr-4 justify-center flex-shrink-0">
         <span className="text-sm font-bold text-gray-700">{charName}</span>
         <span className="text-xs text-gray-400">P{charIndex+1}</span>
      </div>
      <div 
        ref={setNodeRef}
        onMouseMove={(e) => onMouseMove(e, charIndex)}
        onMouseLeave={onMouseLeave}
        className="flex-1 h-12 bg-gray-50/80 rounded-lg relative border border-gray-200 shadow-inner group-hover:border-gray-300 transition-colors"
      >
        {/* Grid Lines Container */}
        <div className="absolute inset-0 overflow-hidden rounded-lg pointer-events-none">
          <div className="absolute inset-0 block">
            {Array.from({ length: Math.ceil(totalDuration) + 1 }).map((_, i) => (
               <div 
                  key={i} 
                  className={cn(
                    "absolute top-0 bottom-0 border-r pointer-events-none",
                    i % 5 === 0 ? "border-gray-300 z-10" : "border-gray-100"
                  )}
                  style={{ left: `${(i / totalDuration) * 100}%` }}
               />
            ))}
          </div>
        </div>

        {/* Hover Indicator (Ghost Cursor) */}
        {isHoveredTrack && hoveredTime !== null && (
          <div 
            className="absolute top-0 bottom-0 w-px bg-blue-400 z-20 pointer-events-none"
            style={{ left: `${(hoveredTime / totalDuration) * 100}%` }}
          >
             <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-blue-100 text-blue-700 text-[10px] px-1.5 py-0.5 rounded border border-blue-200 font-mono shadow-sm z-[9999]">
               {hoveredTime.toFixed(1)}s
               <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1.5 h-1.5 bg-blue-100 border-r border-b border-blue-200 rotate-45"></div>
             </div>
          </div>
        )}

        {/* Actions Container */}
        <div className="absolute inset-0 overflow-visible">
            {actions.map(action => (
              <ActionBlock 
                key={action.id} 
                action={action} 
                charIndex={charIndex}
                totalDuration={totalDuration} 
                containerWidth={trackWidth}
                onDoubleClick={onActionDoubleClick}
              />
            ))}
        </div>
      </div>
    </div>
  );
};

export const TimelineEditor: React.FC = () => {
  const { characters, duration, updateTimelineAction, addTimelineAction, removeTimelineAction, result } = useSimulationStore();
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  
  // SP Calculation based on history snapshots
  const currentSP = React.useMemo(() => {
      // 1. Try to get from result history
      if (result?.history) {
          const frame = result.history.find(h => {
              const t = h.tick / 10.0;
              return t >= currentTime;
          });
          if (frame) return frame.sp;
      }
      
      // 2. Fallback estimation (Prediction for planning)
      // Initial 200, Regen 8 per sec, Max 300
      return Math.min(300, 200 + 8 * currentTime);
  }, [result, currentTime]);

  const requestRef = useRef<number>();
  const previousTimeRef = useRef<number>();
  const trackContainerRef = useRef<HTMLDivElement>(null);
  const [trackWidth, setTrackWidth] = useState(1000);

  // New state for interaction
  const [hoveredTrackInfo, setHoveredTrackInfo] = useState<{ index: number, time: number } | null>(null);
  const [editingAction, setEditingAction] = useState<{ charIndex: number, action: TimelineAction } | null>(null);

  // Measure track width once mounted for accurate drag calcs
  useEffect(() => {
    if (trackContainerRef.current) {
        const updateWidth = () => {
            if(trackContainerRef.current) {
                setTrackWidth(trackContainerRef.current.offsetWidth - 96); // 96px = w-24
            }
        };
        updateWidth();
        window.addEventListener('resize', updateWidth);
        return () => window.removeEventListener('resize', updateWidth);
    }
  }, []);

  // Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = async (e: KeyboardEvent) => {
      // Ignore if input is focused or modal is open (editingAction is not null)
      if (editingAction || (e.target as HTMLElement).tagName === 'INPUT' || (e.target as HTMLElement).tagName === 'TEXTAREA') return;

      if (hoveredTrackInfo) {
        let type: ActionType | null = null;
        let name = "";

        switch(e.key.toLowerCase()) {
           case 's': type = "Skill"; name = "skill"; break;
           case 'u': type = "Ult"; name = "ult"; break;
           case 'q': type = "QTE"; name = "qte"; break;
           case 'a': type = "Attack"; name = "a1"; break;
           case '1': type = "Attack"; name = "a1"; break;
           case '2': type = "Skill"; name = "skill"; break;
           case '3': type = "Ult"; name = "ult"; break;
           case '4': type = "QTE"; name = "qte"; break;
        }

        if (type) {
           const charName = characters[hoveredTrackInfo.index].name;
           const durationVal = await getActionDuration(charName, type);

           addTimelineAction(hoveredTrackInfo.index, {
              type,
              name,
              startTime: hoveredTrackInfo.time, // Already snapped in onMouseMove
              duration: durationVal
           });
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [hoveredTrackInfo, editingAction, addTimelineAction, characters]);

  const handleTrackMouseMove = (e: React.MouseEvent, charIndex: number) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const rawTime = (x / rect.width) * duration;
    // Snap to 0.1s
    const snappedTime = Math.round(rawTime * 10) / 10;
    
    setHoveredTrackInfo({
       index: charIndex,
       time: Math.max(0, Math.min(duration, snappedTime))
    });
  };

  const handleTrackMouseLeave = () => {
    setHoveredTrackInfo(null);
  };

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 1,
      },
    })
  );

  // Custom modifier to restrict dragging within timeline boundaries
  const restrictToTimelineBounds: Modifier = ({ transform, active }) => {
    if (!active || !active.data.current) return transform;

    const action = active.data.current.action as TimelineAction;
    const secondsPerPx = duration / trackWidth;
    const newStartTime = action.startTime + (transform.x * secondsPerPx);

    // Calculate boundaries
    const minX = -action.startTime / secondsPerPx;
    const maxX = (duration - action.startTime - action.duration) / secondsPerPx;

    return {
      ...transform,
      x: Math.max(minX, Math.min(maxX, transform.x)),
    };
  };

  const animate = (time: number) => {
    if (previousTimeRef.current !== undefined) {
      const deltaTime = (time - previousTimeRef.current) / 1000;
      setCurrentTime(prev => {
        const nextTime = prev + deltaTime * playbackSpeed;
        if (nextTime >= duration) {
          setIsPlaying(false);
          return duration;
        }
        return nextTime;
      });
    }
    previousTimeRef.current = time;
    if (isPlaying) {
      requestRef.current = requestAnimationFrame(animate);
    }
  };

  useEffect(() => {
    if (isPlaying) {
      previousTimeRef.current = performance.now();
      requestRef.current = requestAnimationFrame(animate);
    } else {
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
      previousTimeRef.current = undefined;
    }
    return () => {
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
    };
  }, [isPlaying, duration, playbackSpeed]);

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over, delta } = event;
    if (!active || !over) return;

    const charIndex = active.data.current?.charIndex;
    const action = active.data.current?.action as TimelineAction;
    
    const secondsPerPx = duration / trackWidth;
    let newStartTime = action.startTime + (delta.x * secondsPerPx);
    
    // Snap and Clamp
    newStartTime = Math.round(newStartTime * 10) / 10;
    newStartTime = Math.max(0, newStartTime); 
    newStartTime = Math.min(duration - action.duration, newStartTime); 

    updateTimelineAction(charIndex, action.id, { startTime: newStartTime });
  };

  const currentLogs = result?.logs?.filter(log => {
      const timeStr = log.time.replace('[', '').replace(']', '');
      const [min, sec] = timeStr.split(':').map(Number);
      const logTime = min * 60 + sec;
      // Show logs strictly around current time, but allow a slightly larger window for readability during playback
      // Also filter by type: only 'action' and 'damage'
      // Widen the window to 1.5s to ensure logs don't disappear too fast during playback
      const isTimeMatch = logTime <= currentTime && logTime > currentTime - 1.5; 
      const isTypeMatch = log.type === 'action' || log.type === 'damage';
      return isTimeMatch && isTypeMatch;
  }) || [];
  
  const visibleLogs = currentLogs.slice(-5);

  return (
    <div className="flex flex-col h-full gap-4 relative">
      {/* Edit Modal */}
      {editingAction && (
        <EditActionModal 
           action={editingAction.action}
           onSave={(updates) => {
             updateTimelineAction(editingAction.charIndex, editingAction.action.id, updates);
             setEditingAction(null);
           }}
           onDelete={() => {
             removeTimelineAction(editingAction.charIndex, editingAction.action.id);
             setEditingAction(null);
           }}
           onClose={() => setEditingAction(null)}
        />
      )}

      {/* Top Bar: Controls */}
      <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-4">
           <div className="flex bg-gray-100 rounded-lg p-1">
             <button 
                onClick={() => { setIsPlaying(false); setCurrentTime(0); }}
                className="p-2 rounded-md hover:bg-white hover:shadow-sm transition-all text-gray-600"
             >
                <Rewind className="w-5 h-5 fill-current" />
             </button>
             <button 
                onClick={() => { 
                   if(currentTime >= duration) setCurrentTime(0);
                   setIsPlaying(!isPlaying); 
                }}
                className="p-2 rounded-md hover:bg-white hover:shadow-sm transition-all text-blue-600"
             >
                {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current" />}
             </button>
             <button 
                onClick={() => setIsPlaying(false)}
                className="p-2 rounded-md hover:bg-white hover:shadow-sm transition-all text-red-500"
             >
                <Square className="w-4 h-4 fill-current" />
             </button>
           </div>
           
           <div className="flex flex-col">
              <span className="text-xs text-gray-400 font-bold uppercase tracking-wider">Current Time</span>
              <span className="text-2xl font-mono font-bold text-gray-800 w-24">
                {currentTime.toFixed(2)}s
              </span>
           </div>

           <div className="h-8 w-px bg-gray-200 mx-2" />
           
           <div className="flex items-center gap-2">
             <span className="text-xs text-gray-500 font-medium">Speed:</span>
             {[0.5, 1, 2].map(s => (
               <button
                 key={s}
                 onClick={() => setPlaybackSpeed(s)}
                 className={cn(
                   "px-2 py-1 text-xs rounded border transition-colors",
                   playbackSpeed === s ? "bg-blue-100 text-blue-700 border-blue-200" : "bg-white text-gray-600 border-gray-200"
                 )}
               >
                 {s}x
               </button>
             ))}
           </div>
        </div>
        
        {/* Shortcuts Help */}
        <div className="hidden xl:flex items-center gap-4 text-xs text-gray-400">
           <div className="flex items-center gap-1"><span className="border rounded px-1 bg-gray-50">S</span> Skill</div>
           <div className="flex items-center gap-1"><span className="border rounded px-1 bg-gray-50">U</span> Ult</div>
           <div className="flex items-center gap-1"><span className="border rounded px-1 bg-gray-50">Q</span> QTE</div>
           <div className="flex items-center gap-1"><span className="border rounded px-1 bg-gray-50">A</span> Attack</div>
           <div className="flex items-center gap-1 ml-2">Double Click to Edit</div>
        </div>

        {/* Real-time Logs Mini View */}
        <div className="flex-1 ml-8 h-16 bg-gray-900 rounded-lg p-2 overflow-hidden relative">
            <div className="absolute top-2 right-2 text-[10px] text-gray-500 font-mono">LIVE LOGS</div>
            <div className="flex flex-col justify-end h-full">
               {visibleLogs.length === 0 ? (
                 <span className="text-gray-600 text-xs italic">Waiting for events...</span>
               ) : (
                 visibleLogs.map((log, i) => (
                    <div key={i} className="text-xs font-mono truncate animate-in slide-in-from-bottom-2 fade-in duration-300">
                       <span className="text-gray-500 mr-2">{log.time}</span>
                       <span className={cn(
                          log.type === "damage" && "text-yellow-400",
                          log.type === "reaction" && "text-purple-400",
                          log.type === "buff" && "text-blue-400",
                          log.type === "status" && "text-green-400",
                          !["damage", "reaction", "buff", "status"].includes(log.type) && "text-gray-300"
                       )}>{log.message}</span>
                    </div>
                 ))
               )}
            </div>
        </div>
      </div>

      {/* Main Timeline Area */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 flex-1 overflow-y-auto relative select-none">
        <DndContext
          sensors={sensors}
          modifiers={[restrictToHorizontalAxis, restrictToTimelineBounds]}
          onDragEnd={handleDragEnd}
        >
          <div ref={trackContainerRef} id="track-container" className="w-full relative min-h-[400px]">
            
            {/* Playback Cursor Line */}
            <div 
              className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-50 pointer-events-none transition-transform duration-75 shadow-[0_0_10px_rgba(239,68,68,0.6)]"
              style={{ 
                 left: `96px`, // Offset for sidebar
                 width: '2px',
                 transform: `translateX(${(currentTime / duration) * trackWidth}px)`
              }}
            >
               <div className="absolute -top-1 -left-1.5 w-4 h-4 bg-red-500 rounded-full shadow-md border-2 border-white" />
            </div>

            {characters.map((char, idx) => (
               char.name !== "无" && (
                 <TimelineTrack 
                   key={idx} 
                   charIndex={idx} 
                   charName={char.name} 
                   actions={char.timeline || []} 
                   totalDuration={duration} 
                   trackWidth={trackWidth}
                   onMouseMove={handleTrackMouseMove}
                   onMouseLeave={handleTrackMouseLeave}
                   hoveredTime={hoveredTrackInfo?.index === idx ? hoveredTrackInfo.time : null}
                   isHoveredTrack={hoveredTrackInfo?.index === idx}
                   onActionDoubleClick={(action) => setEditingAction({ charIndex: idx, action })}
                 />
               )
            ))}
            
            {/* SP Track (Segmented) */}
            <div className="flex h-10 mb-2 items-center group">
               <div className="w-24 flex flex-col items-end pr-4 justify-center flex-shrink-0">
                  <span className="text-sm font-bold text-yellow-600">SP</span>
                  <span className="text-[10px] text-gray-400 font-mono">{Math.floor(currentSP)}/300</span>
               </div>
               
               <div className="flex-1 flex gap-2 h-3 items-center">
                   {/* Segment 1: 0-100 */}
                   <div className={cn(
                       "flex-1 h-full rounded-full border border-gray-200 bg-gray-100 overflow-hidden relative shadow-inner transition-all duration-300",
                       currentSP >= 100 && "ring-2 ring-yellow-200 shadow-[0_0_10px_rgba(250,204,21,0.5)] border-yellow-300"
                   )}>
                       <div 
                         className="h-full bg-yellow-400 transition-all duration-100 ease-linear"
                         style={{ width: `${Math.min(100, Math.max(0, currentSP) / 100 * 100)}%` }}
                       />
                   </div>

                   {/* Segment 2: 100-200 */}
                   <div className={cn(
                       "flex-1 h-full rounded-full border border-gray-200 bg-gray-100 overflow-hidden relative shadow-inner transition-all duration-300",
                       currentSP >= 200 && "ring-2 ring-yellow-200 shadow-[0_0_10px_rgba(250,204,21,0.5)] border-yellow-300"
                   )}>
                       <div 
                         className="h-full bg-yellow-400 transition-all duration-100 ease-linear"
                         style={{ width: `${Math.min(100, Math.max(0, currentSP - 100) / 100 * 100)}%` }}
                       />
                   </div>

                   {/* Segment 3: 200-300 */}
                   <div className={cn(
                       "flex-1 h-full rounded-full border border-gray-200 bg-gray-100 overflow-hidden relative shadow-inner transition-all duration-300",
                       currentSP >= 300 && "ring-2 ring-yellow-200 shadow-[0_0_10px_rgba(250,204,21,0.5)] border-yellow-300"
                   )}>
                       <div 
                         className="h-full bg-yellow-400 transition-all duration-100 ease-linear"
                         style={{ width: `${Math.min(100, Math.max(0, currentSP - 200) / 100 * 100)}%` }}
                       />
                   </div>
               </div>
            </div>

            {/* Time Axis */}
            <div className="flex text-sm text-gray-400 mt-4 border-t pt-2 h-8">
               <div className="w-24 flex-shrink-0" />
               <div className="flex-1 relative">
                 {Array.from({ length: Math.ceil(duration / 5) + 1 }).map((_, i) => (
                    <div 
                      key={i} 
                      className="absolute top-0"
                      style={{ left: `${(i * 5 / duration) * 100}%` }}
                    >
                      <span className="absolute -left-2 font-mono">{i * 5}s</span>
                      <div className="h-2 w-px bg-gray-300 absolute left-0 -top-2" />
                    </div>
                 ))}
               </div>
            </div>
          </div>
        </DndContext>
      </div>
    </div>
  );
};
