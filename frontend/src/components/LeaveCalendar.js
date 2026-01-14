import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  Calendar as CalendarIcon, ChevronLeft, ChevronRight, 
  CalendarOff, Thermometer, Users, Clock
} from 'lucide-react';

const MONTH_NAMES = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];
const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

// Generate consistent colors for staff members
const STAFF_COLORS = [
  { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-300' },
  { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-300' },
  { bg: 'bg-purple-100', text: 'text-purple-700', border: 'border-purple-300' },
  { bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-300' },
  { bg: 'bg-pink-100', text: 'text-pink-700', border: 'border-pink-300' },
  { bg: 'bg-cyan-100', text: 'text-cyan-700', border: 'border-cyan-300' },
  { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-300' },
  { bg: 'bg-indigo-100', text: 'text-indigo-700', border: 'border-indigo-300' },
];

export default function LeaveCalendar() {
  const [loading, setLoading] = useState(true);
  const [calendarData, setCalendarData] = useState({});
  const [staffList, setStaffList] = useState([]);
  const [totalLeaveDays, setTotalLeaveDays] = useState(0);
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth() + 1);
  const [selectedDate, setSelectedDate] = useState(null);
  const [staffColorMap, setStaffColorMap] = useState({});

  useEffect(() => {
    loadCalendarData();
  }, [currentYear, currentMonth]);

  useEffect(() => {
    // Assign colors to staff members
    const colorMap = {};
    staffList.forEach((staff, index) => {
      colorMap[staff.id] = STAFF_COLORS[index % STAFF_COLORS.length];
    });
    setStaffColorMap(colorMap);
  }, [staffList]);

  const loadCalendarData = async () => {
    setLoading(true);
    try {
      const response = await api.get('/leave/calendar', {
        params: { year: currentYear, month: currentMonth }
      });
      setCalendarData(response.data.calendar_data);
      setStaffList(response.data.staff_list);
      setTotalLeaveDays(response.data.total_leave_days);
    } catch (error) {
      console.error('Failed to load calendar data:', error);
      toast.error('Failed to load leave calendar');
    } finally {
      setLoading(false);
    }
  };

  const goToPreviousMonth = () => {
    if (currentMonth === 1) {
      setCurrentMonth(12);
      setCurrentYear(currentYear - 1);
    } else {
      setCurrentMonth(currentMonth - 1);
    }
    setSelectedDate(null);
  };

  const goToNextMonth = () => {
    if (currentMonth === 12) {
      setCurrentMonth(1);
      setCurrentYear(currentYear + 1);
    } else {
      setCurrentMonth(currentMonth + 1);
    }
    setSelectedDate(null);
  };

  const goToToday = () => {
    const now = new Date();
    setCurrentYear(now.getFullYear());
    setCurrentMonth(now.getMonth() + 1);
    setSelectedDate(null);
  };

  // Generate calendar grid
  const generateCalendarDays = () => {
    const firstDayOfMonth = new Date(currentYear, currentMonth - 1, 1);
    const lastDayOfMonth = new Date(currentYear, currentMonth, 0);
    const daysInMonth = lastDayOfMonth.getDate();
    const startingDay = firstDayOfMonth.getDay();
    
    const days = [];
    
    // Add empty cells for days before the first day of the month
    for (let i = 0; i < startingDay; i++) {
      days.push({ day: null, date: null });
    }
    
    // Add actual days
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      days.push({
        day,
        date: dateStr,
        leaves: calendarData[dateStr] || []
      });
    }
    
    return days;
  };

  const calendarDays = generateCalendarDays();
  const today = new Date();
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

  // Get leaves for selected date
  const selectedDateLeaves = selectedDate ? (calendarData[selectedDate] || []) : [];

  if (loading && Object.keys(calendarData).length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="leave-calendar-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Leave Calendar</h1>
          <p className="text-slate-500 text-sm mt-1">View all approved staff leave days</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-4 py-2 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg flex items-center gap-2">
            <Users size={18} />
            <span className="font-medium">{totalLeaveDays} day(s) with leave this month</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Calendar */}
        <div className="lg:col-span-3 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
          {/* Calendar Header */}
          <div className="px-4 py-3 bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
            <button
              onClick={goToPreviousMonth}
              className="p-2 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors text-slate-600 dark:text-slate-400"
            >
              <ChevronLeft size={20} />
            </button>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
                {MONTH_NAMES[currentMonth - 1]} {currentYear}
              </h2>
              <button
                onClick={goToToday}
                className="px-3 py-1 text-sm bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 rounded-full hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
              >
                Today
              </button>
            </div>
            <button
              onClick={goToNextMonth}
              className="p-2 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors text-slate-600 dark:text-slate-400"
            >
              <ChevronRight size={20} />
            </button>
          </div>

          {/* Day Headers */}
          <div className="grid grid-cols-7 bg-slate-100 dark:bg-slate-700">
            {DAY_NAMES.map(day => (
              <div key={day} className="px-2 py-2 text-center text-sm font-medium text-slate-600 dark:text-slate-400">
                {day}
              </div>
            ))}
          </div>

          {/* Calendar Grid */}
          <div className="grid grid-cols-7">
            {calendarDays.map((dayData, index) => (
              <div
                key={index}
                onClick={() => dayData.date && setSelectedDate(dayData.date)}
                className={`
                  min-h-[100px] p-2 border-b border-r border-slate-100 dark:border-slate-700 transition-colors
                  ${!dayData.day ? 'bg-slate-50 dark:bg-slate-900/50' : 'hover:bg-slate-50 dark:hover:bg-slate-700 cursor-pointer'}
                  ${dayData.date === todayStr ? 'bg-blue-50/50 dark:bg-blue-900/20' : ''}
                  ${dayData.date === selectedDate ? 'ring-2 ring-blue-500 ring-inset' : ''}
                `}
              >
                {dayData.day && (
                  <>
                    <div className={`
                      text-sm font-medium mb-1
                      ${dayData.date === todayStr ? 'text-blue-600 dark:text-blue-400' : 'text-slate-700 dark:text-slate-300'}
                    `}>
                      {dayData.day}
                    </div>
                    <div className="space-y-1">
                      {dayData.leaves?.slice(0, 3).map((leave, i) => {
                        const colors = staffColorMap[leave.staff_id] || STAFF_COLORS[0];
                        return (
                          <div
                            key={i}
                            className={`
                              px-1.5 py-0.5 rounded text-xs truncate
                              ${colors.bg} ${colors.text} ${colors.border} border
                            `}
                            title={`${leave.staff_name} - ${leave.leave_type === 'off_day' ? 'Off Day' : 'Sakit'}`}
                          >
                            {leave.leave_type === 'off_day' ? (
                              <CalendarOff size={10} className="inline mr-1" />
                            ) : (
                              <Thermometer size={10} className="inline mr-1" />
                            )}
                            {leave.staff_name.split(' ')[0]}
                          </div>
                        );
                      })}
                      {dayData.leaves?.length > 3 && (
                        <div className="text-xs text-slate-500 dark:text-slate-400 pl-1">
                          +{dayData.leaves.length - 3} more
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Sidebar - Selected Date Details & Legend */}
        <div className="space-y-4">
          {/* Selected Date Details */}
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="px-4 py-3 bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700">
              <h3 className="font-semibold text-slate-800 dark:text-white flex items-center gap-2">
                <CalendarIcon size={18} />
                {selectedDate ? (
                  <span>{new Date(selectedDate + 'T00:00:00').toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}</span>
                ) : (
                  <span>Select a date</span>
                )}
              </h3>
            </div>
            <div className="p-4">
              {selectedDate ? (
                selectedDateLeaves.length > 0 ? (
                  <div className="space-y-3">
                    {selectedDateLeaves.map((leave, i) => {
                      const colors = staffColorMap[leave.staff_id] || STAFF_COLORS[0];
                      return (
                        <div key={i} className={`p-3 rounded-lg border ${colors.border} ${colors.bg}`}>
                          <div className="flex items-center gap-2 mb-2">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${leave.leave_type === 'off_day' ? 'bg-blue-200' : 'bg-red-200'}`}>
                              {leave.leave_type === 'off_day' ? (
                                <CalendarOff size={16} className="text-blue-700" />
                              ) : (
                                <Thermometer size={16} className="text-red-700" />
                              )}
                            </div>
                            <div>
                              <div className={`font-medium ${colors.text}`}>{leave.staff_name}</div>
                              <div className="text-xs text-slate-500 dark:text-slate-400">
                                {leave.leave_type === 'off_day' ? 'Off Day' : 'Sakit'}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                            <Clock size={14} />
                            <span>{leave.hours_deducted} hours</span>
                            {leave.leave_type === 'sakit' && leave.start_time && (
                              <span className="text-xs">({leave.start_time} - {leave.end_time})</span>
                            )}
                          </div>
                          {leave.reason && (
                            <div className="mt-2 text-xs text-slate-500 dark:text-slate-400 italic">
                              &quot;{leave.reason}&quot;
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-center py-6 text-slate-500 dark:text-slate-400">
                    <CalendarIcon size={32} className="mx-auto mb-2 opacity-30" />
                    <p>No approved leave on this date</p>
                  </div>
                )
              ) : (
                <div className="text-center py-6 text-slate-500 dark:text-slate-400">
                  <CalendarIcon size={32} className="mx-auto mb-2 opacity-30" />
                  <p>Click on a date to see details</p>
                </div>
              )}
            </div>
          </div>

          {/* Staff Legend */}
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="px-4 py-3 bg-slate-50 dark:bg-slate-900 border-b border-slate-200">
              <h3 className="font-semibold text-slate-800 dark:text-white flex items-center gap-2">
                <Users size={18} />
                Staff Legend
              </h3>
            </div>
            <div className="p-4">
              {staffList.length > 0 ? (
                <div className="space-y-2">
                  {staffList.map((staff, index) => {
                    const colors = STAFF_COLORS[index % STAFF_COLORS.length];
                    return (
                      <div key={staff.id} className="flex items-center gap-2">
                        <div className={`w-4 h-4 rounded ${colors.bg} ${colors.border} border`}></div>
                        <span className="text-sm text-slate-700 dark:text-slate-200">{staff.name}</span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">No staff members</p>
              )}
            </div>
          </div>

          {/* Leave Type Legend */}
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="px-4 py-3 bg-slate-50 dark:bg-slate-900 border-b border-slate-200">
              <h3 className="font-semibold text-slate-800 dark:text-white dark:text-slate-100">Leave Types</h3>
            </div>
            <div className="p-4 space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded bg-blue-100 flex items-center justify-center">
                  <CalendarOff size={14} className="text-blue-600" />
                </div>
                <span className="text-sm text-slate-700 dark:text-slate-200">Off Day (12 hours)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded bg-red-100 flex items-center justify-center">
                  <Thermometer size={14} className="text-red-600" />
                </div>
                <span className="text-sm text-slate-700 dark:text-slate-200">Sakit (Custom hours)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
