import { motion } from "framer-motion";
import { StatsComponentProps } from "../types/memory";

export function OperationsStats({ stats, className }: StatsComponentProps) {
  const maxValue = Math.max(
    stats.operations.promotions,
    stats.operations.demotions,
    stats.operations.merges,
    stats.operations.retrievals
  );

  const getBarHeight = (value: number) => {
    return (value / maxValue) * 320; // 320px is max height
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
        <div className="relative z-10 space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold text-white">
              Memory Operations
            </h3>
          </div>

          {/* Top Stats */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm text-muted-foreground">Avg Recall</div>
              <div className="text-2xl font-bold text-purple-500/80">
                {stats.operations.avg_recall_time.toFixed(0)}
                <span className="text-sm font-normal text-muted-foreground ml-1">ms</span>
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Compressions</div>
              <div className="text-2xl font-bold text-green-500/80">
                {stats.operations.compression_count}
              </div>
            </div>
          </div>

          {/* Bar Chart */}
          <div className="h-[400px] flex items-end justify-between gap-6 pt-8">
            <div className="flex flex-col items-center gap-2">
              <div 
                className="w-16 bg-blue-500/80 rounded-t"
                style={{ height: `${getBarHeight(stats.operations.promotions)}px` }}
              />
              <div className="text-sm text-muted-foreground">Promotions</div>
              <div className="text-sm font-semibold text-blue-500/80">
                {stats.operations.promotions}
              </div>
            </div>
            <div className="flex flex-col items-center gap-2">
              <div 
                className="w-16 bg-yellow-500/80 rounded-t"
                style={{ height: `${getBarHeight(stats.operations.demotions)}px` }}
              />
              <div className="text-sm text-muted-foreground">Demotions</div>
              <div className="text-sm font-semibold text-yellow-500/80">
                {stats.operations.demotions}
              </div>
            </div>
            <div className="flex flex-col items-center gap-2">
              <div 
                className="w-16 bg-green-500/80 rounded-t"
                style={{ height: `${getBarHeight(stats.operations.merges)}px` }}
              />
              <div className="text-sm text-muted-foreground">Merges</div>
              <div className="text-sm font-semibold text-green-500/80">
                {stats.operations.merges}
              </div>
            </div>
            <div className="flex flex-col items-center gap-2">
              <div 
                className="w-16 bg-purple-500/80 rounded-t"
                style={{ height: `${getBarHeight(stats.operations.retrievals)}px` }}
              />
              <div className="text-sm text-muted-foreground">Retrievals</div>
              <div className="text-sm font-semibold text-purple-500/80">
                {stats.operations.retrievals}
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