import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { UserPlus, Users, CheckCircle, XCircle, Trash2, Search } from 'lucide-react';

export default function ReservedMemberCRM({ isStaff = false }) {
  const [members, setMembers] = useState([]);
  const [pendingRequests, setPendingRequests] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newMemberName, setNewMemberName] = useState('');
  const [selectedStaff, setSelectedStaff] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [membersRes, usersRes] = await Promise.all([
        api.get('/reserved-members'),
        api.get('/auth/me').then(() => api.get('/auth/me')).catch(() => ({ data: null }))
      ]);

      const approved = membersRes.data.filter(m => m.status === 'approved');
      const pending = membersRes.data.filter(m => m.status === 'pending');
      
      setMembers(approved);
      setPendingRequests(pending);

      // Get staff list for admin
      if (!isStaff) {
        // For now, we'll build staff list from existing reservations
        const uniqueStaff = [...new Set(approved.map(m => JSON.stringify({ id: m.staff_id, name: m.staff_name })))];
        setStaffList(uniqueStaff.map(s => JSON.parse(s)));
      }
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleAddMember = async (e) => {
    e.preventDefault();
    
    if (!newMemberName.trim()) {
      toast.error('Please enter customer ID');
      return;
    }

    if (!isStaff && !selectedStaff) {
      toast.error('Please select a staff member');
      return;
    }

    try {
      await api.post('/reserved-members', {
        customer_id: newMemberName.trim(),
        staff_id: isStaff ? undefined : selectedStaff
      });
      
      if (isStaff) {
        toast.success('Reservation request submitted for approval');
      } else {
        toast.success('Member reserved successfully');
      }
      
      setNewMemberName('');
      setSelectedStaff('');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add reservation');
    }
  };

  const handleApprove = async (memberId) => {
    try {
      await api.patch(`/reserved-members/${memberId}/approve`);
      toast.success('Reservation approved');
      loadData();
    } catch (error) {
      toast.error('Failed to approve');
    }
  };

  const handleReject = async (memberId) => {
    try {
      await api.patch(`/reserved-members/${memberId}/reject`);
      toast.success('Reservation rejected');
      loadData();
    } catch (error) {
      toast.error('Failed to reject');
    }
  };

  const handleDelete = async (memberId) => {
    if (!window.confirm('Are you sure you want to delete this reservation?')) return;
    
    try {
      await api.delete(`/reserved-members/${memberId}`);
      toast.success('Reservation deleted');
      loadData();
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  const filteredMembers = members.filter(m => {
    // Support both customer_id (new) and customer_name (legacy data)
    const customerIdentifier = m.customer_id || m.customer_name || '';
    return customerIdentifier.toLowerCase().includes(search.toLowerCase()) ||
           m.staff_name.toLowerCase().includes(search.toLowerCase());
  });

  // Group by staff
  const membersByStaff = filteredMembers.reduce((acc, member) => {
    if (!acc[member.staff_id]) {
      acc[member.staff_id] = {
        staff_name: member.staff_name,
        members: []
      };
    }
    acc[member.staff_id].members.push(member);
    return acc;
  }, {});

  if (loading) {
    return <div className="text-center py-12">Loading...</div>;
  }

  return (
    <div>
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 mb-6">Reserved Member CRM</h2>

      {/* Add New Member */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 mb-6 shadow-sm">
        <h3 className="text-xl font-semibold text-slate-900 mb-4 flex items-center gap-2">
          <UserPlus className="text-indigo-600" size={20} />
          {isStaff ? 'Request to Reserve Member' : 'Add Reserved Member'}
        </h3>
        <form onSubmit={handleAddMember} className="flex gap-3">
          <input
            type="text"
            value={newMemberName}
            onChange={(e) => setNewMemberName(e.target.value)}
            placeholder="Enter customer name"
            data-testid="new-member-name"
            className="flex-1 h-10 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
          />
          {!isStaff && (
            <select
              value={selectedStaff}
              onChange={(e) => setSelectedStaff(e.target.value)}
              data-testid="select-staff"
              className="h-10 w-64 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
            >
              <option value="">Select Staff</option>
              {staffList.map((staff) => (
                <option key={staff.id} value={staff.id}>
                  {staff.name}
                </option>
              ))}
            </select>
          )}
          <button
            type="submit"
            data-testid="add-member-button"
            className="bg-slate-900 text-white hover:bg-slate-800 shadow-sm font-medium px-6 py-2 rounded-md transition-all active:scale-95"
          >
            {isStaff ? 'Request' : 'Add'}
          </button>
        </form>
        {isStaff && (
          <p className="text-sm text-slate-500 mt-3">
            Your request will be sent to admin for approval before appearing in the list.
          </p>
        )}
      </div>

      {/* Pending Requests (Admin Only) */}
      {!isStaff && pendingRequests.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 mb-6">
          <h3 className="text-xl font-semibold text-amber-900 mb-4">Pending Requests ({pendingRequests.length})</h3>
          <div className="space-y-3">
            {pendingRequests.map((request) => (
              <div key={request.id} className="bg-white rounded-lg p-4 flex items-center justify-between">
                <div>
                  <p className="font-semibold text-slate-900">{request.customer_id || request.customer_name}</p>
                  <p className="text-sm text-slate-600">Requested by: {request.staff_name}</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleApprove(request.id)}
                    data-testid={`approve-${request.id}`}
                    className="bg-emerald-50 text-emerald-600 hover:bg-emerald-100 border border-emerald-200 font-medium px-4 py-2 rounded-md transition-colors flex items-center gap-2"
                  >
                    <CheckCircle size={16} />
                    Approve
                  </button>
                  <button
                    onClick={() => handleReject(request.id)}
                    data-testid={`reject-${request.id}`}
                    className="bg-rose-50 text-rose-600 hover:bg-rose-100 border border-rose-200 font-medium px-4 py-2 rounded-md transition-colors flex items-center gap-2"
                  >
                    <XCircle size={16} />
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Search */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by customer or staff name..."
            className="flex h-10 w-full rounded-md border border-slate-200 bg-white pl-10 pr-3 py-2 text-sm ring-offset-white placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
          />
        </div>
      </div>

      {/* Reserved Members by Staff */}
      <div className="space-y-6">
        {Object.entries(membersByStaff).length === 0 ? (
          <div className="text-center py-12 text-slate-600">
            <Users className="mx-auto text-slate-300 mb-4" size={64} />
            <p>No reserved members yet</p>
          </div>
        ) : (
          Object.entries(membersByStaff).map(([staffId, data]) => (
            <div key={staffId} className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
                    <Users className="text-indigo-600" size={18} />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-slate-900">{data.staff_name}</h3>
                    <p className="text-sm text-slate-600">{data.members.length} reserved members</p>
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {data.members.map((member) => (
                  <div
                    key={member.id}
                    className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200 hover:bg-slate-100 transition-colors"
                  >
                    <span className="font-medium text-slate-900">{member.customer_id || member.customer_name}</span>
                    {!isStaff && (
                      <button
                        onClick={() => handleDelete(member.id)}
                        className="text-rose-600 hover:text-rose-700"
                        title="Delete"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
