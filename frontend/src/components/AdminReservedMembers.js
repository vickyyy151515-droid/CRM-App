import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { UserPlus, Check, X, Trash2, ArrowRight, Search, Users, Clock, CheckCircle } from 'lucide-react';

export default function AdminReservedMembers() {
  const [members, setMembers] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [customerName, setCustomerName] = useState('');
  const [selectedStaff, setSelectedStaff] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [moveModal, setMoveModal] = useState({ open: false, member: null });
  const [newStaffId, setNewStaffId] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [membersRes, staffRes] = await Promise.all([
        api.get('/reserved-members'),
        api.get('/staff-users')
      ]);
      setMembers(membersRes.data);
      setStaffList(staffRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleAddMember = async (e) => {
    e.preventDefault();
    if (!customerName.trim() || !selectedStaff) {
      toast.error('Please fill all fields');
      return;
    }

    setSubmitting(true);
    try {
      await api.post('/reserved-members', {
        customer_name: customerName.trim(),
        staff_id: selectedStaff
      });
      toast.success('Customer reserved successfully');
      setCustomerName('');
      setSelectedStaff('');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add reserved member');
    } finally {
      setSubmitting(false);
    }
  };

  const handleApprove = async (memberId) => {
    try {
      await api.patch(`/reserved-members/${memberId}/approve`);
      toast.success('Request approved');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to approve');
    }
  };

  const handleReject = async (memberId) => {
    try {
      await api.patch(`/reserved-members/${memberId}/reject`);
      toast.success('Request rejected');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reject');
    }
  };

  const handleDelete = async (memberId) => {
    if (!window.confirm('Are you sure you want to delete this reservation?')) return;
    
    try {
      await api.delete(`/reserved-members/${memberId}`);
      toast.success('Reservation deleted');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete');
    }
  };

  const handleMove = async () => {
    if (!newStaffId) {
      toast.error('Please select a staff member');
      return;
    }
    
    try {
      await api.patch(`/reserved-members/${moveModal.member.id}/move?new_staff_id=${newStaffId}`);
      toast.success('Reservation moved successfully');
      setMoveModal({ open: false, member: null });
      setNewStaffId('');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to move');
    }
  };

  const filteredMembers = members.filter(m => {
    const matchesFilter = filter === 'all' || m.status === filter;
    const matchesSearch = m.customer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          m.staff_name.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const pendingCount = members.filter(m => m.status === 'pending').length;
  const approvedCount = members.filter(m => m.status === 'approved').length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div data-testid="admin-reserved-members">
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 mb-6">Reserved Member CRM</h2>
      
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <Users className="text-indigo-600" size={20} />
            <span className="text-2xl font-bold text-slate-900">{members.length}</span>
          </div>
          <p className="text-sm text-slate-600 mt-1">Total Reservations</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <Clock className="text-amber-600" size={20} />
            <span className="text-2xl font-bold text-slate-900">{pendingCount}</span>
          </div>
          <p className="text-sm text-slate-600 mt-1">Pending Requests</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <CheckCircle className="text-emerald-600" size={20} />
            <span className="text-2xl font-bold text-slate-900">{approvedCount}</span>
          </div>
          <p className="text-sm text-slate-600 mt-1">Approved</p>
        </div>
      </div>

      {/* Add New Reservation Form */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm mb-6">
        <h3 className="text-lg font-medium text-slate-900 mb-4 flex items-center gap-2">
          <UserPlus size={20} className="text-indigo-600" />
          Add New Reservation
        </h3>
        <form onSubmit={handleAddMember} className="flex flex-col md:flex-row gap-4">
          <input
            type="text"
            placeholder="Customer Name"
            value={customerName}
            onChange={(e) => setCustomerName(e.target.value)}
            className="flex-1 px-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            data-testid="input-customer-name"
          />
          <select
            value={selectedStaff}
            onChange={(e) => setSelectedStaff(e.target.value)}
            className="px-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
            data-testid="select-staff"
          >
            <option value="">Select Staff</option>
            {staffList.map(staff => (
              <option key={staff.id} value={staff.id}>{staff.name}</option>
            ))}
          </select>
          <button
            type="submit"
            disabled={submitting}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors flex items-center gap-2"
            data-testid="btn-add-reservation"
          >
            <UserPlus size={18} />
            {submitting ? 'Adding...' : 'Add Reservation'}
          </button>
        </form>
      </div>

      {/* Filter and Search */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Search by customer or staff name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            data-testid="search-reservations"
          />
        </div>
        <div className="flex gap-2">
          {['all', 'pending', 'approved'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filter === f 
                  ? 'bg-indigo-600 text-white' 
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
              data-testid={`filter-${f}`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Reservations Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <table className="w-full" data-testid="reservations-table">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-600">Customer Name</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-600">Staff</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-600">Status</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-600">Requested By</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-600">Date</th>
              <th className="text-right px-6 py-4 text-sm font-medium text-slate-600">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredMembers.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                  No reservations found
                </td>
              </tr>
            ) : (
              filteredMembers.map(member => (
                <tr key={member.id} className="hover:bg-slate-50" data-testid={`reservation-row-${member.id}`}>
                  <td className="px-6 py-4 font-medium text-slate-900">{member.customer_name}</td>
                  <td className="px-6 py-4 text-slate-600">{member.staff_name}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      member.status === 'approved' 
                        ? 'bg-emerald-100 text-emerald-800' 
                        : 'bg-amber-100 text-amber-800'
                    }`}>
                      {member.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-600">{member.created_by_name}</td>
                  <td className="px-6 py-4 text-slate-500 text-sm">
                    {new Date(member.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-2">
                      {member.status === 'pending' && (
                        <>
                          <button
                            onClick={() => handleApprove(member.id)}
                            className="p-2 text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                            title="Approve"
                            data-testid={`btn-approve-${member.id}`}
                          >
                            <Check size={18} />
                          </button>
                          <button
                            onClick={() => handleReject(member.id)}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            title="Reject"
                            data-testid={`btn-reject-${member.id}`}
                          >
                            <X size={18} />
                          </button>
                        </>
                      )}
                      {member.status === 'approved' && (
                        <button
                          onClick={() => setMoveModal({ open: true, member })}
                          className="p-2 text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                          title="Move to another staff"
                          data-testid={`btn-move-${member.id}`}
                        >
                          <ArrowRight size={18} />
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(member.id)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Delete"
                        data-testid={`btn-delete-${member.id}`}
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Move Modal */}
      {moveModal.open && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" data-testid="move-modal">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">Move Reservation</h3>
            <p className="text-slate-600 mb-4">
              Move <span className="font-medium">{moveModal.member?.customer_name}</span> to another staff member.
            </p>
            <select
              value={newStaffId}
              onChange={(e) => setNewStaffId(e.target.value)}
              className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white mb-4"
              data-testid="select-new-staff"
            >
              <option value="">Select New Staff</option>
              {staffList.filter(s => s.id !== moveModal.member?.staff_id).map(staff => (
                <option key={staff.id} value={staff.id}>{staff.name}</option>
              ))}
            </select>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => { setMoveModal({ open: false, member: null }); setNewStaffId(''); }}
                className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                data-testid="btn-cancel-move"
              >
                Cancel
              </button>
              <button
                onClick={handleMove}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                data-testid="btn-confirm-move"
              >
                Move
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
