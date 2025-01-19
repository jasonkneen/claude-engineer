import { motion } from "framer-motion";
import { StatsComponentProps } from "../types/memory";

export function GenerationsView({ stats, className }: StatsComponentProps) {
  const chartSize = 140;
  const strokeWidth = 35;
  const radius = (chartSize - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  // Calculate metrics
  const compressionRate = stats.operations.compression_count / Math.max(1, stats.generations);
  const avgMemorySize = Math.round(stats.total_tokens / Math.max(1, stats.generations));
  const memoryEfficiency = (stats.operations.merges / Math.max(1, stats.operations.retrievals) * 100);

  // Calculate stroke dasharray for donut segments
  const total = compressionRate + avgMemorySize + memoryEfficiency;
  const getStrokeDashArray = (value: number) => {
    const percentage = (value / total) * 100;
    return `${(percentage * circumference) / 100} ${circumference}`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className={className}
    >
      <div className="relative overflow-hidden rounded-lg p-6 backdrop-blur-md bg-gradient-to-br from-card/30 to-card/10 dark:from-card/20 dark:to-card/5 border border-primary/5 shadow-xl h-full">
        {/* Background gradient effect */}
        <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-white/0 pointer-events-none" />
        
        {/* Content */}
        <div className="relative z-10 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold text-white">
              Memory <span className="text-purple-500">Generations</span>
            </h3>
            <div className="text-sm text-muted-foreground">
              Total Compressions: {stats.operations.compression_count}
            </div>
          </div>

          <div className="flex items-center justify-between">
            {/* Donut Chart */}
            <div className="relative flex-shrink-0" style={{ width: chartSize, height: chartSize }}>
              <svg width={chartSize} height={chartSize} className="transform -rotate-90 drop-shadow-lg">
                {/* Purple segment */}
                <circle
                  cx={chartSize / 2}
                  cy={chartSize / 2}
                  r={radius}
                  fill="none"
                  stroke="rgb(168, 85, 247)"
                  strokeWidth={strokeWidth}
                  strokeDasharray={getStrokeDashArray(compressionRate)}
                  className="transition-all duration-1000"
                />
                {/* Blue segment */}
                <circle
                  cx={chartSize / 2}
                  cy={chartSize / 2}
                  r={radius}
                  fill="none"
                  stroke="rgb(59, 130, 246)"
                  strokeWidth={strokeWidth}
                  strokeDasharray={getStrokeDashArray(avgMemorySize)}
                  strokeDashoffset={-getStrokeDashArray(compressionRate).split(' ')[0]}
                  className="transition-all duration-1000"
                />
                {/* Green segment */}
                <circle
                  cx={chartSize / 2}
                  cy={chartSize / 2}
                  r={radius}
                  fill="none"
                  stroke="rgb(34, 197, 94)"
                  strokeWidth={strokeWidth}
                  strokeDasharray={getStrokeDashArray(memoryEfficiency)}
                  strokeDashoffset={-getStrokeDashArray(avgMemorySize + compressionRate).split(' ')[0]}
                  className="transition-all duration-1000"
                />
              </svg>
            </div>

            {/* Stats List */}
            <div className="flex-1 ml-8 space-y-4">
              <div>
                <div className="text-2xl font-bold text-purple-500">
                  {stats.generations}
                  <span className="text-sm font-normal text-muted-foreground ml-2">generations</span>
                </div>
              </div>
              <div>
                <div className="text-lg font-semibold text-blue-500">
                  {compressionRate.toFixed(2)}
                  <span className="text-sm font-normal text-muted-foreground ml-2">compressions/gen</span>
                </div>
              </div>
              <div>
                <div className="text-lg font-semibold text-green-500">
                  {avgMemorySize.toLocaleString()}
                  <span className="text-sm font-normal text-muted-foreground ml-2">avg tokens</span>
                </div>
              </div>
              <div>
                <div className="text-lg font-semibold text-yellow-500">
                  {memoryEfficiency.toFixed(1)}%
                  <span className="text-sm font-normal text-muted-foreground ml-2">efficiency</span>
                </div>
              </div>
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