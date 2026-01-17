import { Link, useLocation } from 'react-router-dom';
import { Home, MessageSquare, Users, Database, FileText, Settings, ChevronLeft, ChevronRight, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useUIStore } from '@/stores/uiStore';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

const menuItems = [
  { icon: Home, label: 'Dashboard', path: '/ui' },
  { icon: MessageSquare, label: 'Query Chat', path: '/ui/query' },
  { icon: Users, label: 'Tenants', path: '/ui/tenants' },
  { icon: Database, label: 'Datasets', path: '/ui/datasets' },
  { icon: FileText, label: 'Documents', path: '/ui/documents' },
  { icon: Settings, label: 'Settings', path: '/ui/settings' },
  { icon: Info, label: 'About', path: '/ui/about' },
];

export function Sidebar() {
  const location = useLocation();
  const { sidebarCollapsed, toggleSidebar } = useUIStore();

  return (
    <div
      className={cn(
        'flex flex-col h-screen bg-card border-r transition-all duration-300',
        sidebarCollapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Logo/Header */}
      <div className="h-16 flex items-center px-4 border-b justify-between">
        <div
          className={cn(
            'flex items-center gap-2 min-w-0',
            sidebarCollapsed && 'justify-center flex-1'
          )}
        >
          <img
            src="/ui/rag.svg"
            alt="RAGLite"
            className="h-7 w-7 shrink-0"
          />
          {!sidebarCollapsed && (
            <h1 className="text-xl font-bold truncate">RAGLite</h1>
          )}
        </div>
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" onClick={toggleSidebar}>
                {sidebarCollapsed ? (
                  <ChevronRight className="h-5 w-5" />
                ) : (
                  <ChevronLeft className="h-5 w-5" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">
              {sidebarCollapsed ? 'Expand' : 'Collapse'}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto">
        <TooltipProvider delayDuration={0}>
          <ul className="space-y-1 px-2">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path || 
                               (item.path !== '/ui' && location.pathname.startsWith(item.path));

              const linkContent = (
                <Link
                  to={item.path}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2 rounded-md transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'hover:bg-accent hover:text-accent-foreground',
                    sidebarCollapsed && 'justify-center'
                  )}
                >
                  <Icon className="h-5 w-5 shrink-0" />
                  {!sidebarCollapsed && <span>{item.label}</span>}
                </Link>
              );

              return (
                <li key={item.path}>
                  {sidebarCollapsed ? (
                    <Tooltip>
                      <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
                      <TooltipContent side="right">{item.label}</TooltipContent>
                    </Tooltip>
                  ) : (
                    linkContent
                  )}
                </li>
              );
            })}
          </ul>
        </TooltipProvider>
      </nav>

    </div>
  );
}
