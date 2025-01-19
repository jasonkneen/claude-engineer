import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useRef, useMemo } from "react";
import { EventLogProps } from "../types/memory";

export function EventLog({ logs, className }: EventLogProps) {
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Create stable log entries with unique keys
  const logEntries = useMemo(() => {
    return logs.map((log, index) => ({
      ...log,
      uniqueKey: `${log.timestamp}-${log.id}-${index}`,
      formattedTime: new Date(log.timestamp).toLocaleTimeString()
    }));
  }, [logs]);

  useEffect(() => {
    // Auto-scroll to bottom when new logs arrive
    if (logContainerRef.current) {
      const container = logContainerRef.current;
      const isScrolledToBottom = 
        container.scrollHeight - container.clientHeight <= container.scrollTop + 50;
      
      if (isScrolledToBottom) {
        requestAnimationFrame(() => {
          container.scrollTop = container.scrollHeight;
        });
      }
    }
  }, [logs]);

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'error':
        return '⚠️';
      case 'warning':
        return '⚡';
      case 'info':
        return '💡';
      default:
        return '📝';
    }
  };

  const getEventColor = (type: string) => {
    switch (type) {
      case 'error':
        return 'from-red-500/10 to-red-600/5 border-red-500/20 text-red-400';
      case 'warning':
        return 'from-yellow-500/10 to-yellow-600/5 border-yellow-500/20 text-yellow-400';
      case 'info':
        return 'from-blue-500/10 to-blue-600/5 border-blue-500/20 text-blue-400';
      default:
        return 'from-purple-500/10 to-purple-600/5 border-purple-500/20 text-purple-400';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className={`${className} flex flex-col`}
    >
      <div className="relative overflow-hidden rounded-lg flex flex-col h-full backdrop-blur-md bg-gradient-to-br from-card/30 to-card/10 dark:from-card/20 dark:to-card/5 border border-primary/5 shadow-xl">
        {/* Background gradient effect */}
        <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-white/0 pointer-events-none" />
        
        {/* Content */}
        <div className="relative z-10 flex flex-col h-full">
          <div className="p-6 pb-2">
            <h3 className="text-xl font-bold text-white">
              Event Log
            </h3>
          </div>
          
          <div className="flex-1 min-h-0 p-6 pt-0">
            <div 
              ref={logContainerRef}
              className="h-full overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-primary/20 scrollbar-track-secondary/20"
            >
              <AnimatePresence initial={false}>
                {logEntries.map((log) => (
                  <motion.div
                    key={log.uniqueKey}
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ 
                      opacity: 1, 
                      y: 0,
                      transition: {
                        type: 'spring',
                        stiffness: 300,
                        damping: 30
                      }
                    }}
                    exit={{ 
                      opacity: 0,
                      transition: {
                        duration: 0.2
                      }
                    }}
                    className={`
                      relative rounded-lg mb-2
                      bg-gradient-to-br ${getEventColor(log.type)}
                      border border-opacity-20
                      shadow-sm
                    `}
                  >
                    <div className="p-2">
                      <div className="flex items-start gap-3">
                        <span className="text-lg select-none flex-none">
                          {getEventIcon(log.type)}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-foreground/90 break-words">
                            {log.message}
                          </p>
                          <div className="flex flex-wrap items-center gap-2 mt-1 text-xs text-muted-foreground">
                            <time dateTime={log.timestamp}>
                              {log.formattedTime}
                            </time>
                            {log.w3w && (
                              <span className="font-mono bg-primary/5 px-1.5 py-0.5 rounded whitespace-nowrap">
                                w3w: {log.w3w}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
        </div>

        {/* Hover effect overlay */}
        <motion.div
          className="absolute inset-0 bg-white/5 opacity-0 transition-opacity"
          whileHover={{ opacity: 1 }}
        />
      </div>
    </motion.div>
  );
}