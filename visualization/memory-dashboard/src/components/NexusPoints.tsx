import { motion } from "framer-motion";
import { StatsComponentProps } from "../types/memory";

export function NexusPoints({ stats, className }: StatsComponentProps) {
  const total = stats.nexus_points.types.user +
                stats.nexus_points.types.llm +
                stats.nexus_points.types.system;

  const calculatePercentage = (value: number) => ((value / total) * 100) || 0;

  const userPercentage = calculatePercentage(stats.nexus_points.types.user);
  const llmPercentage = calculatePercentage(stats.nexus_points.types.llm);
  const systemPercentage = calculatePercentage(stats.nexus_points.types.system);

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
        <div className="relative z-10 space-y-2">
          <h3 className="text-sm font-medium text-muted-foreground">
            Nexus Points
          </h3>

          <div className="flex items-center justify-between">
            {/* Donut Chart */}
            <div className="relative w-24 h-24">
              <svg
                viewBox="0 0 100 100"
                className="transform -rotate-90 w-full h-full"
              >
                {/* Background circle */}
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="20"
                  className="text-primary/5"
                />
                
                {/* User segment */}
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="20"
                  className="text-blue-500/80"
                  strokeDasharray={`${userPercentage} ${100 - userPercentage}`}
                  strokeDashoffset="25"
                />
                {/* LLM segment */}
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="20"
                  className="text-purple-500/80"
                  strokeDasharray={`${llmPercentage} ${100 - llmPercentage}`}
                  strokeDashoffset={`${25 - userPercentage}`}
                />
                {/* System segment */}
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="20"
                  className="text-green-500/80"
                  strokeDasharray={`${systemPercentage} ${100 - systemPercentage}`}
                  strokeDashoffset={`${25 - userPercentage - llmPercentage}`}
                />
              </svg>
            </div>

            {/* Stats with Labels */}
            <div className="flex-1 ml-4 space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-sm font-medium text-blue-500">User</div>
                <div className="text-lg font-bold text-blue-500">
                  {stats.nexus_points.types.user}
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="text-sm font-medium text-purple-500">LLM</div>
                <div className="text-lg font-bold text-purple-500">
                  {stats.nexus_points.types.llm}
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="text-sm font-medium text-green-500">System</div>
                <div className="text-lg font-bold text-green-500">
                  {stats.nexus_points.types.system}
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
