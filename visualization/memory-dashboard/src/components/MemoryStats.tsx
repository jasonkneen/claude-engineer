import { motion } from "framer-motion";
import { MemoryPoolCard } from "./MemoryPoolCard";
import { StatsComponentProps } from "../types/memory";

export function MemoryStats({ stats }: StatsComponentProps) {
  return (
    <motion.div 
      className="grid gap-4 md:grid-cols-3"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <MemoryPoolCard
        title="Working Memory"
        tokens={stats.pools.working.size}
        blocks={stats.pools.working.count}
        utilization={stats.pools.working.utilization * 100}
        limit={stats.pools.working.limit}
      />
      <MemoryPoolCard
        title="Short-Term Memory"
        tokens={stats.pools.short_term.size}
        blocks={stats.pools.short_term.count}
        utilization={stats.pools.short_term.utilization * 100}
        limit={stats.pools.short_term.limit}
      />
      <MemoryPoolCard
        title="Long-Term Memory"
        tokens={stats.pools.long_term.size}
        blocks={stats.pools.long_term.count}
        utilization={100}
      />
    </motion.div>
  );
}