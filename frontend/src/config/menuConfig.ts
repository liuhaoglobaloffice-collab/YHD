import { LucideIcon } from 'lucide-react';
import {
  LayoutDashboard,
  Users,
  Briefcase,
  BookOpen,
  Workflow,
  Building2,
  Settings,
  HelpCircle,
  BarChart3,
  Activity,
  Bell,
  UserPlus,
  Award,
  Bot,
  Zap,
  Server,
  Cpu,
  FlaskConical,
  Rocket,
  Target,
  DollarSign,
  TrendingUp,
  FileText,
  Upload,
  FolderTree,
  Search,
  Database,
  Brain,
  LayoutGrid,
  Network,
  List,
  PlusCircle,
  Calendar,
  Eye,
  History,
  UserCog,
  Shield,
  Key,
  FileCheck,
  Book,
  Video,
  Mail,
  Mic,
  Languages,
  MonitorSmartphone,
  SmartphoneCharging,
  Sparkles
} from 'lucide-react';

export interface MenuItemLevel3 {
  name: string;
  path: string;
  icon?: LucideIcon;
}

export interface MenuItemLevel2 {
  name: string;
  path: string;
  icon?: LucideIcon;
  children?: MenuItemLevel3[];
}

export interface MenuItemLevel1 {
  name: string;
  path: string;
  icon: LucideIcon;
  children: MenuItemLevel2[];
}

export const menuConfig: MenuItemLevel1[] = [
  {
    name: '系统总览',
    path: '/overview',
    icon: LayoutDashboard,
    children: [
      {
        name: '实时仪表板',
        path: '/overview/dashboard',
        icon: Activity,
        children: [
          { name: '实时监控', path: '/overview/dashboard/realtime' },
          { name: '统计分析', path: '/overview/dashboard/statistics' }
        ]
      },
      {
        name: '性能监控',
        path: '/overview/performance',
        icon: BarChart3,
        children: [
          { name: 'API性能', path: '/overview/performance/api' },
          { name: '数据库性能', path: '/overview/performance/database' }
        ]
      },
      {
        name: '告警中心',
        path: '/overview/alerts',
        icon: Bell,
        children: [
          { name: '告警列表', path: '/overview/alerts/list' },
          { name: '告警规则', path: '/overview/alerts/rules' }
        ]
      }
    ]
  },
  {
    name: 'AI团队',
    path: '/ai-team',
    icon: Users,
    children: [
      {
        name: 'AI员工管理',
        path: '/ai-team/employees',
        icon: UserCog,
        children: [
          { name: '员工列表', path: '/ai-team/employees/list' },
          { name: '添加员工', path: '/ai-team/employees/add', icon: UserPlus },
          { name: '绩效管理', path: '/ai-team/employees/performance', icon: Award }
        ]
      },
      {
        name: 'Agent管理',
        path: '/ai-team/agents',
        icon: Bot,
        children: [
          { name: 'Agent列表', path: '/ai-team/agents/list' },
          { name: '能力管理', path: '/ai-team/agents/capabilities', icon: Zap }
        ]
      },
      {
        name: 'Provider管理',
        path: '/ai-team/providers',
        icon: Server,
        children: [
          { name: 'Provider列表', path: '/ai-team/providers/list' },
          { name: '模型配置', path: '/ai-team/providers/models', icon: Cpu }
        ]
      },
      {
        name: '语音交互',
        path: '/ai-team/voice',
        icon: Mic,
        children: [
          { name: 'Jarvis 控制台', path: '/ai-team/voice/console', icon: Languages }
        ]
      }
    ]
  },
  {
    name: '未来平台',
    path: '/future',
    icon: MonitorSmartphone,
    children: [
      { name: '平台路线图', path: '/future/platform', icon: SmartphoneCharging },
      { name: '桌面端', path: '/future/desktop', icon: MonitorSmartphone },
      { name: '移动端', path: '/future/mobile', icon: SmartphoneCharging },
      { name: 'UI 操作台', path: '/future/console', icon: LayoutGrid },
      { name: '品牌风格', path: '/future/design', icon: Sparkles }
    ]
  },
  {
    name: '业务运营',
    path: '/business',
    icon: Briefcase,
    children: [
      {
        name: '研发管理',
        path: '/business/research',
        icon: FlaskConical,
        children: [
          { name: '研发项目', path: '/business/research/projects' },
          { name: '创新管理', path: '/business/research/innovation', icon: Rocket }
        ]
      },
      {
        name: '销售管理',
        path: '/business/sales',
        icon: Target,
        children: [
          { name: '销售线索', path: '/business/sales/leads' },
          { name: '商机管理', path: '/business/sales/opportunities', icon: DollarSign },
          { name: '客户管理', path: '/business/sales/customers', icon: Users }
        ]
      },
      {
        name: '日常运营',
        path: '/business/operations',
        icon: TrendingUp,
        children: [
          { name: '日常运营', path: '/business/operations/daily' },
          { name: '运营报表', path: '/business/operations/reports', icon: FileText }
        ]
      }
    ]
  },
  {
    name: '知识中心',
    path: '/knowledge',
    icon: BookOpen,
    children: [
      {
        name: '文档管理',
        path: '/knowledge/documents',
        icon: FileText,
        children: [
          { name: '文档列表', path: '/knowledge/documents/list' },
          { name: '上传文档', path: '/knowledge/documents/upload', icon: Upload },
          { name: '分类管理', path: '/knowledge/documents/categories', icon: FolderTree }
        ]
      },
      {
        name: '记忆管理',
        path: '/knowledge/memory',
        icon: Database,
        children: [
          { name: '知识检索', path: '/knowledge/memory/search', icon: Search },
          { name: '记忆管理', path: '/knowledge/memory/manage' }
        ]
      },
      {
        name: 'AI大脑',
        path: '/knowledge/brain',
        icon: Brain,
        children: [
          { name: '实体管理', path: '/knowledge/brain/entities' },
          { name: '关系图谱', path: '/knowledge/brain/graph', icon: Network }
        ]
      }
    ]
  },
  {
    name: '工作流管理',
    path: '/workflow',
    icon: Workflow,
    children: [
      {
        name: '流程设计',
        path: '/workflow/design',
        icon: PlusCircle,
        children: [
          { name: '流程列表', path: '/workflow/design/list' },
          { name: '创建流程', path: '/workflow/design/create' }
        ]
      },
      {
        name: '任务管理',
        path: '/workflow/tasks',
        icon: List,
        children: [
          { name: '任务列表', path: '/workflow/tasks/list' },
          { name: '创建任务', path: '/workflow/tasks/create', icon: PlusCircle },
          { name: '任务日历', path: '/workflow/tasks/calendar', icon: Calendar }
        ]
      },
      {
        name: '执行监控',
        path: '/workflow/monitoring',
        icon: Eye,
        children: [
          { name: '实时监控', path: '/workflow/monitoring/realtime' },
          { name: '执行历史', path: '/workflow/monitoring/history', icon: History }
        ]
      }
    ]
  },
  {
    name: '多租户管理',
    path: '/tenant',
    icon: Building2,
    children: [
      {
        name: '账号管理',
        path: '/tenant/accounts',
        icon: UserCog,
        children: [
          { name: '主账号管理', path: '/tenant/accounts/main' },
          { name: '子账号管理', path: '/tenant/accounts/sub' }
        ]
      },
      {
        name: 'Token管理',
        path: '/tenant/tokens',
        icon: Key,
        children: [
          { name: 'Token池管理', path: '/tenant/tokens/pool' },
          { name: '使用统计', path: '/tenant/tokens/usage', icon: BarChart3 },
          { name: '隐秘调度', path: '/tenant/tokens/stealth', icon: Shield }
        ]
      },
      {
        name: '权限配置',
        path: '/tenant/permissions',
        icon: Shield,
        children: [
          { name: '权限配置', path: '/tenant/permissions' }
        ]
      }
    ]
  },
  {
    name: '系统设置',
    path: '/settings',
    icon: Settings,
    children: [
      {
        name: '系统配置',
        path: '/settings/system',
        icon: Settings,
        children: [
          { name: '通用设置', path: '/settings/system/general' },
          { name: '安全设置', path: '/settings/system/security', icon: Shield }
        ]
      },
      {
        name: '用户管理',
        path: '/settings/users',
        icon: Users,
        children: [
          { name: '用户列表', path: '/settings/users/list' },
          { name: '角色管理', path: '/settings/users/roles', icon: UserCog },
          { name: '权限管理', path: '/settings/users/permissions', icon: Key }
        ]
      },
      {
        name: '审计日志',
        path: '/settings/audit',
        icon: FileCheck,
        children: [
          { name: '审计日志', path: '/settings/audit' }
        ]
      }
    ]
  },
  {
    name: '帮助中心',
    path: '/help',
    icon: HelpCircle,
    children: [
      {
        name: '使用文档',
        path: '/help/docs',
        icon: Book,
        children: [
          { name: '使用文档', path: '/help/docs' }
        ]
      },
      {
        name: '视频教程',
        path: '/help/videos',
        icon: Video,
        children: [
          { name: '视频教程', path: '/help/videos' }
        ]
      },
      {
        name: '技术支持',
        path: '/help/support',
        icon: Mail,
        children: [
          { name: '技术支持', path: '/help/support' }
        ]
      }
    ]
  }
];

/**
 * 根据当前路径生成面包屑导航
 */
export function getBreadcrumbs(pathname: string): Array<{ name: string; path: string }> {
  const breadcrumbs: Array<{ name: string; path: string }> = [];

  for (const l1 of menuConfig) {
    if (pathname.startsWith(l1.path)) {
      breadcrumbs.push({ name: l1.name, path: l1.path });

      for (const l2 of l1.children) {
        if (pathname.startsWith(l2.path)) {
          breadcrumbs.push({ name: l2.name, path: l2.path });

          if (l2.children) {
            for (const l3 of l2.children) {
              if (pathname === l3.path) {
                breadcrumbs.push({ name: l3.name, path: l3.path });
                break;
              }
            }
          }
          break;
        }
      }
      break;
    }
  }

  return breadcrumbs;
}
