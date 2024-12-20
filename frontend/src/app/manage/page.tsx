import { Metadata } from 'next'
import { CreateAgent } from '@/components/tool-management/create-agent'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export const metadata: Metadata = {
  title: 'Manage - Claude Engineer',
  description: 'Manage agents and tools',
}

export default function ManagePage() {
  return (
    <div className="container mx-auto py-6">
      <div className="flex flex-col gap-8">
        <div>
          <h1 className="text-3xl font-bold">Agent Management</h1>
          <p className="text-muted-foreground">Create and manage your AI agents</p>
        </div>

        <Tabs defaultValue="create" className="w-full">
          <TabsList>
            <TabsTrigger value="create">Create Agent</TabsTrigger>
            <TabsTrigger value="manage">Manage Agents</TabsTrigger>
          </TabsList>
          <TabsContent value="create" className="mt-6">
            <CreateAgent />
          </TabsContent>
          <TabsContent value="manage" className="mt-6">
            <div className="text-center text-muted-foreground">
              Agent management interface coming soon
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}