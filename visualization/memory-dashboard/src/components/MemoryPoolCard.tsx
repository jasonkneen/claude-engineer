import { motion } from "framer-motion";
import { cn } from "../lib/utils";
import { ComponentBaseProps } from "../types/memory";

interface MemoryPoolCardProps extends ComponentBaseProps {
  title: string;
  tokens: number;
  blocks: number;
  utilization?: number;
  limit?: number;
}

export function MemoryPoolCard({
  title,
  tokens,
  blocks,
  utilization,
  limit,
  className
}: MemoryPoolCardProps) {
  const getUtilizationColor = (value: number) => {
    if (value >= 90) return 'from-red-500 to-red-600';
    if (value >= 70) return 'from-yellow-500 to-yellow-600';
    if (value >= 50) return 'from-blue-500 to-blue-600';
    return 'from-green-500 to-green-600';
  };

  return (
    <motion.div
      className={cn(
        "relative overflow-hidden rounded-lg p-4 backdrop-blur-md",
        "bg-gradient-to-br from-card/20 to-card/10 dark:from-card/10 dark:to-card/5",
        "border border-primary/10 shadow-xl",
        className
      )}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {/* Background gradient effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-white/0 pointer-events-none" />
      
      {/* Content */}
      <div className="relative z-10">
        <h3 className="text-base font-medium text-muted-foreground mb-3">{title}</h3>

        <div className="flex items-center justify-between mb-4">
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold">
              {tokens.toLocaleString()}
            </span>
            <span className="text-sm text-muted-foreground">tokens</span>
          </div>
          <div className="text-sm text-muted-foreground">
            Blocks: {blocks}
          </div>
        </div>

        {utilization !== undefined && (
          <div className="flex items-center gap-2">
            <div className="flex-1 relative h-1.5 overflow-hidden rounded-full bg-secondary/50">
              <motion.div
                className={cn(
                  "absolute inset-y-0 left-0 bg-gradient-to-r",
                  getUtilizationColor(utilization)
                )}
                initial={{ width: "0%" }}
                animate={{ width: `${utilization}%` }}
                transition={{ duration: 0.8, ease: "easeOut" }}
              >
                <div className="absolute inset-0 bg-white/10" />
              </motion.div>
            </div>
            <div className={cn(
              "text-sm font-medium",
              utilization >= 90 ? "text-red-500" :
              utilization >= 70 ? "text-yellow-500" :
              utilization >= 50 ? "text-blue-500" :
              "text-green-500"
            )}>
              {utilization.toFixed(0)}%
            </div>
          </div>
        )}

        {limit && (
          <div className="text-sm text-muted-foreground mt-2">
            Limit: {limit.toLocaleString()} tokens
          </div>
        )}
      </div>

      {/* Hover effect overlay */}
      <motion.div
        className="absolute inset-0 bg-white/5 opacity-0 transition-opacity"
        whileHover={{ opacity: 1 }}
      />
    </motion.div>
  );
}