import { useEffect, useState } from 'react';
import { MemoryStats } from './components/MemoryStats';
import { OperationsStats } from './components/OperationsStats';
import { NexusPoints } from './components/NexusPoints';
import { EventLog } from './components/EventLog';
import { GenerationsView } from './components/GenerationsView';
import { ThemeToggle } from './components/ui/theme-toggle';
import { useMemoryStats } from './services/memory-service';
import type { LogMessage, StatsMessage } from './types/memory';
import { motion } from 'framer-motion';
import { generateMockEventLogs, generateMockOperationStats } from './lib/mock-data';

function App() {
  const { stats: liveStats, logs: liveLogs, connected } = useMemoryStats();
  const [recentLogs, setRecentLogs] = useState<LogMessage[]>([]);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [demoStats, setDemoStats] = useState<StatsMessage | null>(null);
  const [demoLogs, setDemoLogs] = useState<LogMessage[]>([]);

  // Use either live or demo data based on mode
  const stats = isDemoMode ? demoStats || liveStats : liveStats;
  const logs = isDemoMode ? demoLogs : liveLogs;

  useEffect(() => {
    // Keep only the last 100 logs
    setRecentLogs(prev => {
      const newLogs = [...prev, ...logs].slice(-100);
      return newLogs;
    });
  }, [logs]);

  const handleDemoClick = () => {
    if (!isDemoMode) {
      // Load mock data
      setDemoStats(generateMockOperationStats());
      setDemoLogs(generateMockEventLogs());
      setIsDemoMode(true);
    } else {
      // Return to live data
      setDemoStats(null);
      setDemoLogs([]);
      setIsDemoMode(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-background/95 text-foreground">
      <div className="container mx-auto p-4 flex flex-col gap-3 min-h-screen">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold">
                CORTEX - {' '}
                <span className="bg-gradient-to-r from-primary to-purple-600 bg-clip-text text-transparent">
                  Dashboard
                </span>
              </h1>
              <motion.div
                animate={{
                  scale: connected ? [1, 1.2, 1] : 1,
                  opacity: connected ? 1 : 0.5,
                }}
                transition={{
                  duration: 0.5,
                  repeat: connected ? Infinity : 0,
                  repeatDelay: 2,
                }}
                className={`w-2 h-2 rounded-full ${
                  connected ? 'bg-green-500' : 'bg-red-500'
                }`}
              />
            </div>
            <p className="text-muted-foreground">Nexus Memory Management System</p>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={handleDemoClick}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                ${isDemoMode 
                  ? 'bg-primary/20 text-primary hover:bg-primary/30' 
                  : 'bg-primary text-primary-foreground hover:bg-primary/90'
                }`}
            >
              {isDemoMode ? 'Exit Demo' : 'Demo'}
            </button>
            <ThemeToggle />
          </div>
        </div>

        {/* Main Dashboard Grid */}
        <div className="grid gap-3 md:grid-cols-12">
          {/* Left Column - Memory Generation Chart */}
          <div className="md:col-span-6">
            <GenerationsView
              stats={stats}
              className="h-[400px]"
            />
          </div>

          {/* Right Column - Stats */}
          <div className="md:col-span-6 grid gap-3">
            {/* Top Row - Operation Stats */}
            <div className="grid grid-cols-2 gap-3">
              <OperationsStats
                stats={stats}
                type="recall"
                className="h-[180px]"
              />
              <OperationsStats
                stats={stats}
                type="compression"
                className="h-[180px]"
              />
            </div>

            {/* Middle Row - More Stats */}
            <div className="grid grid-cols-2 gap-3">
              <OperationsStats
                stats={stats}
                type="merges"
                className="h-[180px]"
              />
              <NexusPoints
                stats={stats}
                className="h-[180px]"
              />
            </div>
          </div>
        </div>

        {/* Event Log Row */}
        <div className="h-[300px]">
          <EventLog
            logs={recentLogs}
            className="h-full"
          />
        </div>
      </div>
    </div>
  );
}

export default App;
