import { useState } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { UserPlus, Shield, User, Crown } from 'lucide-react';

export default function CreateUser({ currentUser }) {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    role: 'staff'
  });
  const [loading, setLoading] = useState(false);

  // Role hierarchy levels
  const ROLE_HIERARCHY = {
    'master_admin': 3,
    'admin': 2,
    'staff': 1
  };

  // Get available roles current user can create
  const getAvailableRoles = () => {
    const currentLevel = ROLE_HIERARCHY[currentUser?.role] || 0;
    const roles = [];
    if (currentLevel > ROLE_HIERARCHY['staff']) roles.push({ value: 'staff', label: 'Staff', icon: User });
    if (currentLevel > ROLE_HIERARCHY['admin']) roles.push({ value: 'admin', label: 'Admin', icon: Shield });
    // Only master_admin can create another master_admin (rare)
    if (currentUser?.role === 'master_admin') roles.push({ value: 'master_admin', label: 'Master Admin', icon: Crown });
    return roles;
  };

  const availableRoles = getAvailableRoles();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await api.post('/auth/register', formData);
      toast.success('User created successfully!');
      setFormData({ name: '', email: '', password: '', role: 'staff' });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create user');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  return (
    <div className="max-w-2xl">
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white mb-6">Create New User</h2>

      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-8 shadow-sm">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              Full Name
            </label>
            <input
              id="name"
              name="name"
              type="text"
              value={formData.name}
              onChange={handleChange}
              required
              data-testid="create-user-name-input"
              className="flex h-10 w-full rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white px-3 py-2 text-sm ring-offset-white dark:ring-offset-slate-800 placeholder:text-slate-500 dark:placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
              placeholder="John Doe"
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              Email Address
            </label>
            <input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              required
              data-testid="create-user-email-input"
              className="flex h-10 w-full rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white px-3 py-2 text-sm ring-offset-white dark:ring-offset-slate-800 placeholder:text-slate-500 dark:placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
              placeholder="user@example.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleChange}
              required
              data-testid="create-user-password-input"
              className="flex h-10 w-full rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white px-3 py-2 text-sm ring-offset-white dark:ring-offset-slate-800 placeholder:text-slate-500 dark:placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
              placeholder="Minimum 8 characters"
            />
          </div>

          <div>
            <label htmlFor="role" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              Role
            </label>
            <select
              id="role"
              name="role"
              value={formData.role}
              onChange={handleChange}
              data-testid="create-user-role-select"
              className="flex h-10 w-full rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white px-3 py-2 text-sm ring-offset-white dark:ring-offset-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
            >
              {availableRoles.map(role => (
                <option key={role.value} value={role.value}>{role.label}</option>
              ))}
            </select>
            {currentUser?.role !== 'master_admin' && (
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
                You can only create users with roles below your level
              </p>
            )}
          </div>

          {/* Role description */}
          <div className="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg border border-slate-200 dark:border-slate-600">
            <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Role Permissions:</h4>
            <ul className="text-xs text-slate-600 dark:text-slate-400 space-y-1">
              <li className="flex items-center gap-2">
                <User size={12} className="text-blue-500" />
                <span><strong>Staff</strong> - Can access assigned records and enter OMSET data</span>
              </li>
              <li className="flex items-center gap-2">
                <Shield size={12} className="text-purple-500" />
                <span><strong>Admin</strong> - Full dashboard access, can manage staff users</span>
              </li>
              <li className="flex items-center gap-2">
                <Crown size={12} className="text-amber-500" />
                <span><strong>Master Admin</strong> - Full control, can manage all users and restrict admin access</span>
              </li>
            </ul>
          </div>

          <button
            type="submit"
            disabled={loading}
            data-testid="create-user-submit-button"
            className="w-full bg-slate-900 dark:bg-indigo-600 text-white hover:bg-slate-800 dark:hover:bg-indigo-700 shadow-sm font-medium px-6 py-2.5 rounded-md transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <UserPlus size={18} />
            {loading ? 'Creating User...' : 'Create User'}
          </button>
        </form>
      </div>
    </div>
  );
}