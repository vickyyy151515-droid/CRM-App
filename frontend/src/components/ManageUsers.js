import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Users, Edit2, Trash2, X, Search, Shield, User, Calendar, Activity, FileText, Crown, Lock, Unlock, Settings, ChevronDown, ChevronUp } from 'lucide-react';

// Role hierarchy levels
const ROLE_HIERARCHY = {
  'master_admin': 3,
  'admin': 2,
  'staff': 1
};

export default function ManageUsers({ currentUser }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [editingUser, setEditingUser] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [pageAccessUser, setPageAccessUser] = useState(null);
  const [blockedPages, setBlockedPages] = useState([]);
  const [editForm, setEditForm] = useState({
    name: '',
    email: '',
    password: '',
    role: ''
  });

  // All available pages that can be blocked
  const allPages = [
    { id: 'overview', label: 'Overview' },
    { id: 'leaderboard', label: 'Leaderboard' },
    { id: 'daily-summary', label: 'Daily Summary' },
    { id: 'funnel', label: 'Conversion Funnel' },
    { id: 'retention', label: 'Customer Retention' },
    { id: 'analytics', label: 'Advanced Analytics' },
    { id: 'export', label: 'Export Center' },
    { id: 'scheduled-reports', label: 'Scheduled Reports' },
    { id: 'user-activity', label: 'User Activity' },
    { id: 'report', label: 'CRM Report' },
    { id: 'bonus', label: 'Bonus Calculation' },
    { id: 'leave', label: 'Leave Requests' },
    { id: 'leave-calendar', label: 'Leave Calendar' },
    { id: 'izin-monitor', label: 'Monitor Izin' },
    { id: 'progress', label: 'Staff Progress' },
    { id: 'omset', label: 'OMSET CRM' },
    { id: 'reserved', label: 'Reserved Members' },
    { id: 'bonanza', label: 'DB Bonanza' },
    { id: 'memberwd', label: 'Member WD CRM' },
    { id: 'upload', label: 'Upload Database' },
    { id: 'databases', label: 'Manage Databases' },
    { id: 'assignments', label: 'View Assignments' },
    { id: 'requests', label: 'Download Requests' },
    { id: 'history', label: 'Download History' },
    { id: 'products', label: 'Product Management' },
    { id: 'manage-users', label: 'Manage Users' },
    { id: 'users', label: 'Create User' }
  ];

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const response = await api.get('/users');
      setUsers(response.data);
    } catch (error) {
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  // Check if current user can manage target user based on role hierarchy
  const canManageUser = (targetRole) => {
    const currentLevel = ROLE_HIERARCHY[currentUser?.role] || 0;
    const targetLevel = ROLE_HIERARCHY[targetRole] || 0;
    return currentLevel > targetLevel;
  };

  // Get available roles current user can assign
  const getAvailableRoles = () => {
    const currentLevel = ROLE_HIERARCHY[currentUser?.role] || 0;
    const roles = [];
    if (currentLevel > ROLE_HIERARCHY['staff']) roles.push('staff');
    if (currentLevel > ROLE_HIERARCHY['admin']) roles.push('admin');
    // master_admin can only be assigned by another master_admin (rare case)
    return roles;
  };

  const handleEdit = (user) => {
    if (!canManageUser(user.role)) {
      toast.error(`You don't have permission to edit ${user.role} users`);
      return;
    }
    setEditingUser(user);
    setEditForm({
      name: user.name,
      email: user.email,
      password: '',
      role: user.role
    });
  };

  const handleSaveEdit = async () => {
    try {
      const updateData = {};
      if (editForm.name !== editingUser.name) updateData.name = editForm.name;
      if (editForm.email !== editingUser.email) updateData.email = editForm.email;
      if (editForm.password) updateData.password = editForm.password;
      if (editForm.role !== editingUser.role) updateData.role = editForm.role;

      if (Object.keys(updateData).length === 0) {
        toast.info('No changes to save');
        setEditingUser(null);
        return;
      }

      await api.put(`/users/${editingUser.id}`, updateData);
      toast.success('User updated successfully');
      setEditingUser(null);
      loadUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update user');
    }
  };

  const handleDelete = async (userId) => {
    try {
      await api.delete(`/users/${userId}`);
      toast.success('User deleted successfully');
      setDeleteConfirm(null);
      loadUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete user');
    }
  };

  // Page access management (Master Admin only)
  const handleOpenPageAccess = async (user) => {
    if (user.role !== 'admin') {
      toast.error('Page access control is only available for admin users');
      return;
    }
    try {
      // Use query parameter endpoint to avoid route conflicts
      const response = await api.get(`/page-access?user_id=${user.id}`);
      setBlockedPages(response.data.blocked_pages || []);
      setPageAccessUser(user);
    } catch (error) {
      console.error('Page access error:', error.response?.data || error.message);
      toast.error(error.response?.data?.detail || 'Failed to load page access settings');
    }
  };

  const handleSavePageAccess = async () => {
    try {
      // Use query parameter endpoint to avoid route conflicts
      await api.put(`/page-access?user_id=${pageAccessUser.id}`, {
        blocked_pages: blockedPages
      });
      toast.success('Page access updated successfully');
      setPageAccessUser(null);
      loadUsers();
    } catch (error) {
      console.error('Save page access error:', error.response?.data || error.message);
      toast.error(error.response?.data?.detail || 'Failed to update page access');
    }
  };

  const togglePageBlock = (pageId) => {
    if (blockedPages.includes(pageId)) {
      setBlockedPages(blockedPages.filter(p => p !== pageId));
    } else {
      setBlockedPages([...blockedPages, pageId]);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleDateString('id-ID', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = roleFilter === 'all' || user.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  const staffCount = users.filter(u => u.role === 'staff').length;
  const adminCount = users.filter(u => u.role === 'admin').length;
  const masterAdminCount = users.filter(u => u.role === 'master_admin').length;

  const getRoleBadge = (role) => {
    switch (role) {
      case 'master_admin':
        return {
          bgClass: 'bg-gradient-to-r from-amber-100 to-yellow-100 dark:from-amber-900/50 dark:to-yellow-900/50',
          textClass: 'text-amber-800 dark:text-amber-300',
          icon: <Crown size={12} className="mr-1" />,
          label: 'Master Admin'
        };
      case 'admin':
        return {
          bgClass: 'bg-purple-100 dark:bg-purple-900/50',
          textClass: 'text-purple-800 dark:text-purple-300',
          icon: <Shield size={12} className="mr-1" />,
          label: 'Admin'
        };
      default:
        return {
          bgClass: 'bg-blue-100 dark:bg-blue-900/50',
          textClass: 'text-blue-800 dark:text-blue-300',
          icon: <User size={12} className="mr-1" />,
          label: 'Staff'
        };
    }
  };

  const getAvatarColor = (role) => {
    switch (role) {
      case 'master_admin':
        return 'bg-gradient-to-br from-amber-400 to-yellow-500';
      case 'admin':
        return 'bg-purple-500';
      default:
        return 'bg-indigo-500';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div data-testid="manage-users">
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white mb-6">Manage Users</h2>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-xl p-4 text-white shadow-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-indigo-100 text-sm">Total Users</p>
              <p className="text-2xl font-bold">{users.length}</p>
            </div>
            <Users className="opacity-80" size={32} />
          </div>
        </div>
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-4 text-white shadow-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-100 text-sm">Staff Members</p>
              <p className="text-2xl font-bold">{staffCount}</p>
            </div>
            <User className="opacity-80" size={32} />
          </div>
        </div>
        <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl p-4 text-white shadow-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-100 text-sm">Administrators</p>
              <p className="text-2xl font-bold">{adminCount}</p>
            </div>
            <Shield className="opacity-80" size={32} />
          </div>
        </div>
        <div className="bg-gradient-to-br from-amber-500 to-yellow-500 rounded-xl p-4 text-white shadow-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-amber-100 text-sm">Master Admins</p>
              <p className="text-2xl font-bold">{masterAdminCount}</p>
            </div>
            <Crown className="opacity-80" size={32} />
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 shadow-sm mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              type="text"
              placeholder="Search by name or email..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full h-10 pl-10 pr-4 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              data-testid="search-users-input"
            />
          </div>
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            data-testid="filter-role-select"
          >
            <option value="all">All Roles</option>
            <option value="staff">Staff Only</option>
            <option value="admin">Admin Only</option>
            <option value="master_admin">Master Admin Only</option>
          </select>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">User</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">Role</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-700 dark:text-slate-300">Assigned Records</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-700 dark:text-slate-300">OMSET Records</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">Last Activity</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">Created</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-700 dark:text-slate-300">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-slate-500 dark:text-slate-400">
                    No users found
                  </td>
                </tr>
              ) : (
                filteredUsers.map(user => {
                  const roleBadge = getRoleBadge(user.role);
                  const canEdit = canManageUser(user.role);
                  const hasBlockedPages = user.blocked_pages && user.blocked_pages.length > 0;
                  
                  return (
                    <tr key={user.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/50" data-testid={`user-row-${user.id}`}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold ${getAvatarColor(user.role)}`}>
                            {user.name.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <p className="font-medium text-slate-900 dark:text-white">{user.name}</p>
                            <p className="text-sm text-slate-500 dark:text-slate-400">{user.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${roleBadge.bgClass} ${roleBadge.textClass}`}>
                            {roleBadge.icon}
                            {roleBadge.label}
                          </span>
                          {hasBlockedPages && (
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300" title={`${user.blocked_pages.length} pages blocked`}>
                              <Lock size={10} className="mr-0.5" />
                              {user.blocked_pages.length}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="inline-flex items-center px-2 py-1 rounded bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 text-sm">
                          <FileText size={14} className="mr-1" />
                          {user.assigned_records || 0}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="inline-flex items-center px-2 py-1 rounded bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 text-sm">
                          {user.omset_records || 0}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1 text-sm text-slate-600 dark:text-slate-400">
                          <Activity size={14} />
                          {formatDate(user.last_activity)}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1 text-sm text-slate-600 dark:text-slate-400">
                          <Calendar size={14} />
                          {formatDate(user.created_at)}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-1">
                          {canEdit && (
                            <>
                              <button
                                onClick={() => handleEdit(user)}
                                className="p-2 text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 rounded-lg transition-colors"
                                title="Edit User"
                                data-testid={`edit-user-${user.id}`}
                              >
                                <Edit2 size={16} />
                              </button>
                              {/* Page Access button - only for master_admin editing admin users */}
                              {currentUser?.role === 'master_admin' && user.role === 'admin' && (
                                <button
                                  onClick={() => handleOpenPageAccess(user)}
                                  className="p-2 text-slate-600 dark:text-slate-400 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/30 rounded-lg transition-colors"
                                  title="Manage Page Access"
                                  data-testid={`page-access-${user.id}`}
                                >
                                  <Settings size={16} />
                                </button>
                              )}
                              <button
                                onClick={() => setDeleteConfirm(user)}
                                className="p-2 text-slate-600 dark:text-slate-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                                title="Delete User"
                                data-testid={`delete-user-${user.id}`}
                              >
                                <Trash2 size={16} />
                              </button>
                            </>
                          )}
                          {!canEdit && (
                            <span className="text-xs text-slate-400 dark:text-slate-500 px-2">
                              No permission
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Modal */}
      {editingUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" data-testid="edit-user-modal">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Edit User</h3>
              <button
                onClick={() => setEditingUser(null)}
                className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              >
                <X size={20} />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Name</label>
                <input
                  type="text"
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  className="w-full h-10 px-3 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  data-testid="edit-user-name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Email</label>
                <input
                  type="email"
                  value={editForm.email}
                  onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                  className="w-full h-10 px-3 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  data-testid="edit-user-email"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  New Password <span className="text-slate-400 font-normal">(leave blank to keep current)</span>
                </label>
                <input
                  type="password"
                  value={editForm.password}
                  onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
                  placeholder="Enter new password"
                  className="w-full h-10 px-3 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  data-testid="edit-user-password"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Role</label>
                <select
                  value={editForm.role}
                  onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
                  className="w-full h-10 px-3 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  data-testid="edit-user-role"
                >
                  {getAvailableRoles().map(role => (
                    <option key={role} value={role}>
                      {role === 'master_admin' ? 'Master Admin' : role.charAt(0).toUpperCase() + role.slice(1)}
                    </option>
                  ))}
                </select>
                {currentUser?.role !== 'master_admin' && (
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    You can only assign roles below your level
                  </p>
                )}
              </div>
            </div>
            <div className="flex justify-end gap-3 px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
              <button
                onClick={() => setEditingUser(null)}
                className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors"
                data-testid="save-edit-user"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Page Access Modal (Master Admin Only) */}
      {pageAccessUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" data-testid="page-access-modal">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
              <div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                  <Settings size={20} className="text-amber-500" />
                  Page Access Control
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  Managing access for <span className="font-medium">{pageAccessUser.name}</span>
                </p>
              </div>
              <button
                onClick={() => setPageAccessUser(null)}
                className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              >
                <X size={20} />
              </button>
            </div>
            <div className="p-6 overflow-y-auto flex-1">
              <div className="mb-4 p-3 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg">
                <p className="text-sm text-amber-800 dark:text-amber-300">
                  <strong>Note:</strong> Blocked pages will be hidden from this admin's sidebar and they won't be able to access them.
                </p>
              </div>
              
              <div className="space-y-2">
                {allPages.map(page => {
                  const isBlocked = blockedPages.includes(page.id);
                  return (
                    <div
                      key={page.id}
                      className={`flex items-center justify-between p-3 rounded-lg border transition-colors cursor-pointer ${
                        isBlocked 
                          ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800' 
                          : 'bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-600 hover:border-slate-300 dark:hover:border-slate-500'
                      }`}
                      onClick={() => togglePageBlock(page.id)}
                      data-testid={`page-toggle-${page.id}`}
                    >
                      <span className={`text-sm font-medium ${
                        isBlocked 
                          ? 'text-red-700 dark:text-red-300 line-through' 
                          : 'text-slate-700 dark:text-slate-300'
                      }`}>
                        {page.label}
                      </span>
                      {isBlocked ? (
                        <Lock size={16} className="text-red-500" />
                      ) : (
                        <Unlock size={16} className="text-emerald-500" />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="flex justify-between items-center px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
              <div className="text-sm text-slate-600 dark:text-slate-400">
                {blockedPages.length} page(s) blocked
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setPageAccessUser(null)}
                  className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSavePageAccess}
                  className="px-4 py-2 text-sm font-medium text-white bg-amber-600 hover:bg-amber-700 rounded-lg transition-colors"
                  data-testid="save-page-access"
                >
                  Save Access Settings
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" data-testid="delete-user-modal">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl w-full max-w-sm mx-4">
            <div className="p-6">
              <div className="w-12 h-12 rounded-full bg-red-100 dark:bg-red-900/50 flex items-center justify-center mx-auto mb-4">
                <Trash2 className="text-red-600 dark:text-red-400" size={24} />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white text-center mb-2">Delete User</h3>
              <p className="text-sm text-slate-600 dark:text-slate-400 text-center mb-1">
                Are you sure you want to delete <span className="font-semibold">{deleteConfirm.name}</span>?
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-500 text-center">
                This action cannot be undone.
              </p>
            </div>
            <div className="flex border-t border-slate-200 dark:border-slate-700">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="flex-1 px-4 py-3 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm.id)}
                className="flex-1 px-4 py-3 text-sm font-medium text-white bg-red-600 hover:bg-red-700 transition-colors"
                data-testid="confirm-delete-user"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
