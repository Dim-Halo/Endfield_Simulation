import React, { useState, useEffect, useRef } from 'react';
import { ConfigView } from './components/ConfigView';
import { TimelineView } from './components/TimelineView';
import { SimulationResults } from './components/SimulationResults';
import { OperatorManagement } from './components/OperatorManagement';
import { useSimulationStore } from './store/useSimulationStore';
import { apiClient } from './api/client';
import { Play, Loader2, Settings, BarChart2, Clock, Users } from 'lucide-react';
import clsx from 'clsx';

function App() {
  const {
    duration,
    enemy,
    characters,
    result,
    isSimulating,
    setResult,
    setIsSimulating,
    generateScriptFromTimeline,
    fetchAvailableCharacters,
    fetchWeapons
  } = useSimulationStore();

  const [currentView, setCurrentView] = useState<'config' | 'timeline' | 'results' | 'operators'>('config');

  useEffect(() => {
    fetchAvailableCharacters();
    fetchWeapons();
  }, []);

  const runSimulation = async (showLoading = true) => {
    if (showLoading) setIsSimulating(true);
    try {
      const payloadCharacters = characters.map((c, idx) => {
         if (c.name === "无") return null;

         let scriptToSend = c.script;
         if (c.timeline && c.timeline.length > 0) {
            scriptToSend = generateScriptFromTimeline(idx);
         }

         return {
            name: c.name,
            script: scriptToSend,
            molten_stacks: c.molten_stacks,
            custom_attrs: c.custom_attrs,
            weapon_id: c.weapon_id
         };
      }).filter(Boolean);

      const payload = {
        duration,
        enemy,
        characters: payloadCharacters
      };
      
      const response = await apiClient.post('/simulate', payload);
      setResult(response.data);
      // Do NOT switch view automatically on auto-run
    } catch (error: any) {
      console.error("Simulation failed:", error);
    } finally {
      if (showLoading) setIsSimulating(false);
    }
  };

  useEffect(() => {
    // Use setTimeout instead of lodash.debounce to avoid closure staleness issues
    // When 'characters' changes, this effect runs, clearing the old timer and setting a new one.
    // The runSimulation call inside the timeout will use the *current* render's scope (with latest characters).
    const timer = setTimeout(() => {
        runSimulation(false); // Run silently
    }, 500);
    
    return () => clearTimeout(timer);
  }, [characters, duration, enemy]);

  const handleManualRun = async () => {
      await runSimulation(true);
      setCurrentView('results');
  };

  return (
    <div className="flex h-screen bg-gray-100 overflow-hidden font-sans text-gray-900">
      
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Header / Toolbar */}
        <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between shadow-sm z-10">
          <div className="flex items-center gap-6">
            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              终末地战斗模拟器
            </h1>
            
            {/* View Switcher Tabs */}
            <div className="flex bg-gray-100 p-1 rounded-lg">
              <button
                onClick={() => setCurrentView('config')}
                className={clsx(
                  "px-4 py-1.5 text-sm font-medium rounded-md transition-all flex items-center gap-2",
                  currentView === 'config' ? "bg-white text-blue-600 shadow-sm" : "text-gray-500 hover:text-gray-700"
                )}
              >
                <Settings className="w-4 h-4" /> 编队与设置
              </button>
              <button
                onClick={() => setCurrentView('timeline')}
                className={clsx(
                  "px-4 py-1.5 text-sm font-medium rounded-md transition-all flex items-center gap-2",
                  currentView === 'timeline' ? "bg-white text-blue-600 shadow-sm" : "text-gray-500 hover:text-gray-700"
                )}
              >
                <Clock className="w-4 h-4" /> 排轴编辑
              </button>
              <button
                onClick={() => setCurrentView('operators')}
                className={clsx(
                  "px-4 py-1.5 text-sm font-medium rounded-md transition-all flex items-center gap-2",
                  currentView === 'operators' ? "bg-white text-blue-600 shadow-sm" : "text-gray-500 hover:text-gray-700"
                )}
              >
                <Users className="w-4 h-4" /> 干员管理
              </button>
              <button
                onClick={() => setCurrentView('results')}
                disabled={!result}
                className={clsx(
                  "px-4 py-1.5 text-sm font-medium rounded-md transition-all flex items-center gap-2",
                  currentView === 'results' ? "bg-white text-blue-600 shadow-sm" : "text-gray-500 hover:text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                )}
              >
                <BarChart2 className="w-4 h-4" /> 模拟结果
              </button>
            </div>
          </div>
          
          <button
            onClick={handleManualRun}
            disabled={isSimulating}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-6 py-2 rounded-lg font-medium shadow-md transition-all flex items-center gap-2"
          >
            {isSimulating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> 运行中...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" /> 运行/查看结果
              </>
            )}
          </button>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col overflow-hidden relative">

          {currentView === 'config' && <ConfigView />}

          {currentView === 'timeline' && <TimelineView />}

          {currentView === 'operators' && <OperatorManagement />}

          {currentView === 'results' && result && <SimulationResults />}

          {currentView === 'results' && !result && !isSimulating && (
             <div className="flex-1 flex flex-col items-center justify-center text-gray-400 p-12">
               <div className="w-24 h-24 bg-gray-200 rounded-full flex items-center justify-center mb-4 opacity-50">
                 <BarChart2 className="w-10 h-10 text-gray-400 ml-1" />
               </div>
               <p>暂无数据，请先配置角色并运行模拟</p>
               <button 
                 onClick={() => setCurrentView('config')}
                 className="mt-4 text-blue-600 hover:underline text-sm"
               >
                 返回配置页面
               </button>
             </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
