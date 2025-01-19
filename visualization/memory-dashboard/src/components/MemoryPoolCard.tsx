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
        "relative overflow-hidden rounded-lg p-6 backdrop-blur-md",
        "bg-gradient-to-br from-card/80 to-card/40 dark:from-card/40 dark:to-card/20",
        "border border-primary/5 shadow-xl",
        className
      )}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {/* Background gradient effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-white/0 pointer-events-none" />
      
      {/* Content */}
      <div className="relative z-10 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-muted-foreground">{title}</h3>
          <motion.span 
            className="text-sm text-muted-foreground"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            Blocks: {blocks}
          </motion.span>
        </div>

        <motion.div
          className="flex items-baseline gap-1"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
        >
          <span className="text-2xl font-bold gradient-text">
            {tokens.toLocaleString()}
          </span>
          <span className="text-sm text-muted-foreground">tokens</span>
        </motion.div>

        {utilization !== undefined && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Utilization</span>
              <motion.span 
                className={cn(
                  "font-medium",
                  utilization >= 90 ? "text-red-500" :
                  utilization >= 70 ? "text-yellow-500" :
                  utilization >= 50 ? "text-blue-500" :
                  "text-green-500"
                )}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                {utilization.toFixed(1)}%
              </motion.span>
            </div>
            <div className="relative h-2 overflow-hidden rounded-full bg-secondary/50">
              <motion.div
                className={cn(
                  "absolute inset-y-0 left-0 bg-gradient-to-r transition-all duration-500",
                  getUtilizationColor(utilization)
                )}
                initial={{ width: "0%" }}
                animate={{ width: `${utilization}%` }}
                transition={{ duration: 0.8, ease: "easeOut" }}
              >
                <div className="absolute inset-0 bg-white/20" />
                <motion.div
                  className="absolute inset-0 bg-white/20"
                  initial={{ x: "-100%" }}
                  animate={{ x: "100%" }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: "linear"
                  }}
                />
              </motion.div>
            </div>
          </div>
        )}

        {limit && (
          <motion.div 
            className="text-sm text-muted-foreground"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
          >
            Limit: {limit.toLocaleString()} tokens
          </motion.div>
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