import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
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
      <Card className="h-full bg-transparent border-none shadow-none">
        <CardHeader className="p-3">
          <CardTitle className="text-base font-normal text-primary/50">
            Nexus Points
          </CardTitle>
        </CardHeader>
        <CardContent className="relative pt-0 px-3 pb-3">
          {/* Donut Chart */}
          <div className="relative w-48 h-48 mx-auto">
            <svg
              viewBox="0 0 100 100"
              className="transform -rotate-90 w-full h-full"
            >
              {/* Background circle for glass effect */}
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
                className="text-blue-500/80 backdrop-blur-sm"
                strokeDasharray={`${userPercentage} ${100 - userPercentage}`}
                strokeDashoffset="25"
                style={{
                  filter: 'drop-shadow(0 0 8px rgba(59, 130, 246, 0.5))'
                }}
              />
              {/* LLM segment */}
              <circle
                cx="50"
                cy="50"
                r="40"
                fill="none"
                stroke="currentColor"
                strokeWidth="20"
                className="text-purple-500/80 backdrop-blur-sm"
                strokeDasharray={`${llmPercentage} ${100 - llmPercentage}`}
                strokeDashoffset={`${25 - userPercentage}`}
                style={{
                  filter: 'drop-shadow(0 0 8px rgba(168, 85, 247, 0.5))'
                }}
              />
              {/* System segment */}
              <circle
                cx="50"
                cy="50"
                r="40"
                fill="none"
                stroke="currentColor"
                strokeWidth="20"
                className="text-green-500/80 backdrop-blur-sm"
                strokeDasharray={`${systemPercentage} ${100 - systemPercentage}`}
                strokeDashoffset={`${25 - userPercentage - llmPercentage}`}
                style={{
                  filter: 'drop-shadow(0 0 8px rgba(34, 197, 94, 0.5))'
                }}
              />
            </svg>

            {/* Arrows and Labels */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="relative w-full h-full">
                {/* User Arrow */}
                <motion.div 
                  className="absolute -left-4 top-1/2 transform -translate-y-1/2 flex items-center"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 }}
                >
                  <div className="text-blue-500 text-lg mr-2">→</div>
                  <div className="text-sm font-semibold text-blue-500">User</div>
                </motion.div>

                {/* LLM Arrow */}
                <motion.div 
                  className="absolute -right-4 top-1/4 transform -translate-y-1/2 flex items-center"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  <div className="text-sm font-semibold text-purple-500">LLM</div>
                  <div className="text-purple-500 text-lg ml-2">←</div>
                </motion.div>

                {/* System Arrow */}
                <motion.div 
                  className="absolute -right-4 bottom-1/4 transform translate-y-1/2 flex items-center"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.4 }}
                >
                  <div className="text-sm font-semibold text-green-500">System</div>
                  <div className="text-green-500 text-lg ml-2">←</div>
                </motion.div>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 mt-4 text-center">
            <div>
              <div className="text-xl font-bold text-blue-500/80 shadow-blue-500/50">
                {stats.nexus_points.types.user}
              </div>
            </div>
            <div>
              <div className="text-xl font-bold text-purple-500/80 shadow-purple-500/50">
                {stats.nexus_points.types.llm}
              </div>
            </div>
            <div>
              <div className="text-xl font-bold text-green-500/80 shadow-green-500/50">
                {stats.nexus_points.types.system}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}