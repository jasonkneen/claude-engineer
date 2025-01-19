import { motion } from "framer-motion";
import { StatsComponentProps } from "../types/memory";

export function GenerationsView({ stats, className }: StatsComponentProps) {
  const chartSize = 180;
  const strokeWidth = 20;
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
      <div className="relative overflow-hidden rounded-lg p-6 backdrop-blur-md bg-gradient-to-br from-card/80 to-card/40 dark:from-card/40 dark:to-card/20 border border-primary/5 shadow-xl h-full">
        {/* Background gradient effect */}
        <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-white/0 pointer-events-none" />
        
        {/* Content */}
        <div className="relative z-10 space-y-4">
          <h3 className="text-xl font-bold bg-gradient-to-r from-primary to-purple-600 bg-clip-text text-transparent">
            Memory Generations
          </h3>

          <div className="flex flex-col items-center justify-center">
            {/* Donut Chart */}
            <div className="relative" style={{ width: chartSize, height: chartSize }}>
              <svg width={chartSize} height={chartSize} className="transform -rotate-90">
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
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center">
                  <div className="text-4xl font-bold text-purple-500/80">
                    {stats.generations}
                  </div>
                  <div className="text-sm text-muted-foreground">generations</div>
                </div>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-3 gap-4 mt-6 w-full">
              <div className="space-y-2">
                <div className="text-sm text-muted-foreground">Compression Rate</div>
                <div className="text-lg font-semibold text-blue-500/80">
                  {compressionRate.toFixed(2)}
                  <span className="text-xs font-normal text-muted-foreground ml-1">
                    per gen
                  </span>
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-sm text-muted-foreground">Avg Memory Size</div>
                <div className="text-lg font-semibold text-green-500/80">
                  {avgMemorySize.toLocaleString()}
                  <span className="text-xs font-normal text-muted-foreground ml-1">
                    tokens
                  </span>
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-sm text-muted-foreground">Memory Efficiency</div>
                <div className="text-lg font-semibold text-yellow-500/80">
                  {memoryEfficiency.toFixed(1)}%
                  <span className="text-xs font-normal text-muted-foreground ml-1">
                    merge
                  </span>
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