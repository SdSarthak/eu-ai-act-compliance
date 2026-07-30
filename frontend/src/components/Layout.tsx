import { Outlet, Link, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../stores/authStore'
import { billingApi } from '../services/api'
import {
  LayoutDashboard,
  Bot,
  FileCheck,
  FileText,
  ClipboardList,
  CreditCard,
  LogOut,
  Shield,
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'AI Systems', href: '/ai-systems', icon: Bot },
  { name: 'Risk Classification', href: '/classification', icon: FileCheck },
  { name: 'Compliance', href: '/compliance', icon: ClipboardList },
  { name: 'Documents', href: '/documents', icon: FileText },
  { name: 'Plans & Billing', href: '/billing', icon: CreditCard },
]

export default function Layout() {
  const location = useLocation()
  const { user, logout } = useAuthStore()

  const { data: subscription } = useQuery({
    queryKey: ['subscription'],
    queryFn: billingApi.subscription,
  })

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 w-64 bg-white border-r border-gray-200 flex flex-col">
        {/* Logo */}
        <div className="flex items-center gap-2 px-6 py-4 border-b border-gray-200">
          <Shield className="w-8 h-8 text-primary-600" />
          <span className="text-lg font-semibold text-gray-900">
            AI Compliance
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-1 p-4 flex-1">
          {navigation.map((item) => {
            const isActive =
              item.href === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.href)
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <item.icon className="w-5 h-5" />
                {item.name}
              </Link>
            )
          })}
        </nav>

        {/* User section */}
        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center justify-between gap-2">
            <div className="truncate">
              <p className="text-sm font-medium text-gray-900 truncate">
                {user?.full_name || user?.email}
              </p>
              <p className="text-xs text-gray-500 truncate">
                {user?.company_name || 'No company set'}
              </p>
              {subscription && (
                <Link
                  to="/billing"
                  className="inline-block mt-1 text-xs px-2 py-0.5 rounded-full bg-primary-50 text-primary-700"
                >
                  {subscription.plan_name} plan
                </Link>
              )}
            </div>
            <button
              onClick={logout}
              title="Sign out"
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="pl-64">
        <main className="p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
