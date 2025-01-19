import { motion } from "framer-motion";
import { StatsComponentProps } from "../types/memory";

interface OperationsStatsProps extends StatsComponentProps {
  type: 'recall' | 'compression' | 'merges' | 'retrievals';
}

export function OperationsStats({ stats, type, className }: OperationsStatsProps) {
  const getStatContent = () => {
    switch (type) {
      case 'recall':
        return {
          title: 'Average Recall Time',
          value: stats.operations.avg_recall_time.toFixed(0),
          unit: 'ms',
          color: 'purple'
        };
      case 'compression':
        return {
          title: 'Compressions',
          value: stats.operations.compression_count.toString(),
          unit: 'total',
          color: 'green'
        };
      case 'merges':
        return {
          title: 'Memory Merges',
          value: stats.operations.merges.toString(),
          unit: 'ops',
          color: 'blue'
        };
      case 'retrievals':
        return {
          title: 'Retrievals',
          value: stats.operations.retrievals.toString(),
          unit: 'ops',
          color: 'yellow'
        };
      default:
        return {
          title: '',
          value: '0',
          unit: '',
          color: 'gray'
        };
    }
  };

  const content = getStatContent();
  const colorClass = `text-${content.color}-500/80`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className={className}
    >
      <div className="relative overflow-hidden rounded-lg p-4 backdrop-blur-md bg-gradient-to-br from-card/30 to-card/10 dark:from-card/20 dark:to-card/5 border border-primary/5 shadow-xl h-full">
        {/* Background gradient effect */}
        <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-white/0 pointer-events-none" />
        
        {/* Content */}
        <div className="relative z-10 flex flex-col justify-between h-full">
          <h3 className="text-sm font-medium text-muted-foreground">
            {content.title}
          </h3>
          
          <div className="mt-2">
            <div className={`text-3xl font-bold ${colorClass}`}>
              {content.value}
            </div>
            <div className="text-sm text-muted-foreground mt-1">
              {content.unit}
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