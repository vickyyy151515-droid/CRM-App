/**
 * Fee & Payment Tab Component
 * Displays lateness fee summary and management interface
 */
import { useState, useCallback, useEffect } from 'react';
import { api } from '../../App';
import { toast } from 'sonner';
import { 
  Clock, DollarSign, CreditCard, Users, RefreshCw,
  Plus, Settings, CheckCircle
} from 'lucide-react';
import StaffFeeCard from './StaffFeeCard';
import { 
  WaiveFeeModal, 
  InstallmentModal, 
  ManualFeeModal, 
  PaymentModal, 
  CurrencyModal 
} from './FeeModals';

export default function FeePaymentTab() {
  const [feeData, setFeeData] = useState(null);
  const [feeYear, setFeeYear] = useState(new Date().getFullYear());
  const [feeMonth, setFeeMonth] = useState(new Date().getMonth() + 1);
  const [expandedFeeStaff, setExpandedFeeStaff] = useState(null);
  const [processingFee, setProcessingFee] = useState(null);
  
  // Modal states
  const [waiveModal, setWaiveModal] = useState(null);
  const [waiveReason, setWaiveReason] = useState('');
  const [installmentModal, setInstallmentModal] = useState(null);
  const [installmentMonths, setInstallmentMonths] = useState(2);
  
  // Manual fee & payment state
  const [staffList, setStaffList] = useState([]);
  const [manualFeeModal, setManualFeeModal] = useState(false);
  const [manualFeeStaffId, setManualFeeStaffId] = useState('');
  const [manualFeeAmount, setManualFeeAmount] = useState('');
  const [manualFeeReason, setManualFeeReason] = useState('');
  const [paymentModal, setPaymentModal] = useState(null);
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentCurrency, setPaymentCurrency] = useState('USD');
  const [paymentNote, setPaymentNote] = useState('');
  const [currencyModal, setCurrencyModal] = useState(false);
  const [thbRate, setThbRate] = useState(3100);
  const [idrRate, setIdrRate] = useState(16700);

  // Fetch fee summary
  const fetchFees = useCallback(async () => {
    try {
      const response = await api.get(`/attendance/admin/fees/summary?year=${feeYear}&month=${feeMonth}`);
      setFeeData(response.data);
      if (response.data.currency_rates) {
        setThbRate(response.data.currency_rates.THB);
        setIdrRate(response.data.currency_rates.IDR);
      }
    } catch (error) {
      console.error('Error fetching fees:', error);
      toast.error('Failed to load fee data');
    }
  }, [feeYear, feeMonth]);

  // Fetch staff list for manual fees
  const fetchStaffList = useCallback(async () => {
    try {
      const response = await api.get('/attendance/admin/fees/staff-list');
      setStaffList(response.data.staff || []);
    } catch (error) {
      console.error('Error fetching staff list:', error);
    }
  }, []);

  useEffect(() => {
    fetchFees();
    fetchStaffList();
  }, [fetchFees, fetchStaffList]);

  // Format currency
  const formatCurrency = (amount, currency = 'USD') => {
    if (currency === 'USD') return `$${amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    if (currency === 'THB') return `฿${Math.round(amount).toLocaleString()}`;
    if (currency === 'IDR') return `Rp ${Math.round(amount).toLocaleString()}`;
    return amount;
  };

  // Waive fee for a specific date
  const handleWaiveFee = async (staffId, date) => {
    if (!waiveReason.trim()) {
      toast.error('Please provide a reason for waiving the fee');
      return;
    }
    setProcessingFee(`${staffId}-${date}`);
    try {
      await api.post(`/attendance/admin/fees/${staffId}/waive?date=${date}`, {
        reason: waiveReason
      });
      toast.success('Fee waived successfully');
      setWaiveModal(null);
      setWaiveReason('');
      fetchFees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to waive fee');
    } finally {
      setProcessingFee(null);
    }
  };

  // Remove izin overage fee for a specific date
  const handleRemoveIzinFee = async (staffId, date, staffName) => {
    if (!window.confirm(`Remove izin overage fee for ${staffName} on ${date}?`)) return;
    setProcessingFee(`izin-${staffId}-${date}`);
    try {
      await api.post(`/attendance/admin/fees/${staffId}/waive-izin?date=${date}`);
      toast.success('Izin overage fee removed');
      fetchFees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to remove izin fee');
    } finally {
      setProcessingFee(null);
    }
  };

  // Setup installment plan
  const handleSetupInstallment = async (staffId) => {
    setProcessingFee(`installment-${staffId}`);
    try {
      await api.post(`/attendance/admin/fees/${staffId}/installment?year=${feeYear}&month=${feeMonth}`, {
        num_months: installmentMonths
      });
      toast.success(`Installment plan created for ${installmentMonths} month(s)`);
      setInstallmentModal(null);
      fetchFees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to setup installment');
    } finally {
      setProcessingFee(null);
    }
  };

  // Cancel installment plan
  const handleCancelInstallment = async (staffId) => {
    if (!window.confirm('Cancel this installment plan?')) return;
    setProcessingFee(`cancel-installment-${staffId}`);
    try {
      await api.delete(`/attendance/admin/fees/${staffId}/installment?year=${feeYear}&month=${feeMonth}`);
      toast.success('Installment plan cancelled');
      fetchFees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to cancel installment');
    } finally {
      setProcessingFee(null);
    }
  };

  // Record payment for installment
  const handleRecordInstallmentPayment = async (staffId, paymentMonth) => {
    setProcessingFee(`pay-${staffId}-${paymentMonth}`);
    try {
      await api.post(`/attendance/admin/fees/${staffId}/pay?year=${feeYear}&month=${feeMonth}&payment_month=${paymentMonth}`);
      toast.success('Payment recorded successfully');
      fetchFees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record payment');
    } finally {
      setProcessingFee(null);
    }
  };

  // Add manual fee
  const handleAddManualFee = async () => {
    if (!manualFeeStaffId || !manualFeeAmount || !manualFeeReason) {
      toast.error('Please fill in all fields');
      return;
    }
    setProcessingFee('manual-fee');
    try {
      await api.post(`/attendance/admin/fees/${manualFeeStaffId}/manual?year=${feeYear}&month=${feeMonth}`, {
        amount_usd: parseFloat(manualFeeAmount),
        reason: manualFeeReason
      });
      toast.success('Manual fee added successfully');
      setManualFeeModal(false);
      setManualFeeStaffId('');
      setManualFeeAmount('');
      setManualFeeReason('');
      fetchFees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add manual fee');
    } finally {
      setProcessingFee(null);
    }
  };

  // Delete manual fee
  const handleDeleteManualFee = async (feeId) => {
    if (!window.confirm('Delete this manual fee?')) return;
    setProcessingFee(`delete-manual-${feeId}`);
    try {
      await api.delete(`/attendance/admin/fees/manual/${feeId}`);
      toast.success('Manual fee deleted');
      fetchFees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete manual fee');
    } finally {
      setProcessingFee(null);
    }
  };

  // Record partial payment
  const handleRecordPartialPayment = async () => {
    if (!paymentAmount) {
      toast.error('Please enter payment amount');
      return;
    }
    setProcessingFee(`partial-payment-${paymentModal.staff_id}`);
    try {
      await api.post(`/attendance/admin/fees/${paymentModal.staff_id}/payment?year=${feeYear}&month=${feeMonth}`, {
        amount: parseFloat(paymentAmount),
        currency: paymentCurrency,
        note: paymentNote || null
      });
      toast.success('Payment recorded successfully');
      setPaymentModal(null);
      setPaymentAmount('');
      setPaymentCurrency('USD');
      setPaymentNote('');
      fetchFees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record payment');
    } finally {
      setProcessingFee(null);
    }
  };

  // Delete payment
  const handleDeletePayment = async (paymentId) => {
    if (!window.confirm('Delete this payment record?')) return;
    setProcessingFee(`delete-payment-${paymentId}`);
    try {
      await api.delete(`/attendance/admin/fees/payment/${paymentId}`);
      toast.success('Payment deleted');
      fetchFees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete payment');
    } finally {
      setProcessingFee(null);
    }
  };

  // Update currency rates
  const handleUpdateCurrencyRates = async () => {
    setProcessingFee('currency-rates');
    try {
      await api.put('/attendance/admin/fees/currency-rates', {
        thb_rate: parseFloat(thbRate),
        idr_rate: parseFloat(idrRate)
      });
      toast.success('Currency rates updated');
      setCurrencyModal(false);
      fetchFees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update currency rates');
    } finally {
      setProcessingFee(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Month/Year Selector */}
      <div className="flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Year</label>
          <select
            value={feeYear}
            onChange={(e) => setFeeYear(Number(e.target.value))}
            className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
          >
            {[2024, 2025, 2026, 2027].map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Month</label>
          <select
            value={feeMonth}
            onChange={(e) => setFeeMonth(Number(e.target.value))}
            className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
          >
            {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].map((m, idx) => (
              <option key={idx} value={idx + 1}>{m}</option>
            ))}
          </select>
        </div>
        <button
          onClick={fetchFees}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg"
        >
          <RefreshCw size={18} />
          Refresh
        </button>
        <button
          onClick={() => setManualFeeModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg"
        >
          <Plus size={18} />
          Add Manual Fee
        </button>
        <button
          onClick={() => setCurrencyModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-slate-600 hover:bg-slate-700 text-white rounded-lg"
        >
          <Settings size={18} />
          Currency Rates
        </button>
      </div>

      {/* Global Summary Cards */}
      {feeData && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
                  <Clock className="text-red-600" size={24} />
                </div>
                <div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">Late Minutes</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white">{feeData.total_late_minutes}</p>
                </div>
              </div>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
                  <Clock className="text-orange-600" size={24} />
                </div>
                <div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">Izin Overage</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white">{(feeData.total_izin_overage_minutes || 0).toFixed(1)}<span className="text-sm font-normal"> min</span></p>
                </div>
              </div>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
                  <DollarSign className="text-amber-600" size={24} />
                </div>
                <div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">This Month's Fees</p>
                  <p className="text-xl font-bold text-slate-900 dark:text-white">{formatCurrency(feeData.total_fees_this_month, 'USD')}</p>
                  <p className="text-xs text-slate-500">{formatCurrency(feeData.total_fees_this_month_thb, 'THB')} • {formatCurrency(feeData.total_fees_this_month_idr, 'IDR')}</p>
                </div>
              </div>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg">
                  <CreditCard className="text-emerald-600" size={24} />
                </div>
                <div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">Total Collected (All Time)</p>
                  <p className="text-xl font-bold text-emerald-600">{formatCurrency(feeData.total_collected_all_time, 'USD')}</p>
                  <p className="text-xs text-emerald-500">{formatCurrency(feeData.total_collected_all_time_thb, 'THB')} • {formatCurrency(feeData.total_collected_all_time_idr, 'IDR')}</p>
                </div>
              </div>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                  <Users className="text-blue-600" size={24} />
                </div>
                <div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">Staff with Fees</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white">{feeData.staff_count_with_fees}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-slate-100 dark:bg-slate-700/50 rounded-lg p-3 flex flex-wrap justify-center gap-4 text-sm text-slate-600 dark:text-slate-300">
            <span>💰 Fee Rate: <span className="font-bold">${feeData.fee_per_minute}/minute</span> (lateness & izin overage)</span>
            <span>⏱ Izin Limit: <span className="font-bold">{feeData.izin_limit_minutes || 30} min/day</span></span>
            <span>💱 $1 = ฿{thbRate.toLocaleString()} THB = Rp {idrRate.toLocaleString()} IDR</span>
          </div>

          {/* Staff Fee Cards */}
          <div className="space-y-4">
            {feeData.staff_fees.length > 0 ? (
              feeData.staff_fees.map((staff) => (
                <StaffFeeCard
                  key={staff.staff_id}
                  staff={staff}
                  isExpanded={expandedFeeStaff === staff.staff_id}
                  onToggle={() => setExpandedFeeStaff(expandedFeeStaff === staff.staff_id ? null : staff.staff_id)}
                  formatCurrency={formatCurrency}
                  onRecordPayment={setPaymentModal}
                  onSetupInstallment={setInstallmentModal}
                  onCancelInstallment={handleCancelInstallment}
                  onRecordInstallmentPayment={handleRecordInstallmentPayment}
                  onWaiveFee={setWaiveModal}
                  onDeleteManualFee={handleDeleteManualFee}
                  onDeletePayment={handleDeletePayment}
                  processingFee={processingFee}
                />
              ))
            ) : (
              <div className="bg-white dark:bg-slate-800 rounded-xl p-8 text-center text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                <CheckCircle className="mx-auto mb-2 text-emerald-500" size={32} />
                <p>No lateness or izin overage fees for this month!</p>
              </div>
            )}
          </div>
        </>
      )}

      {/* Modals */}
      <WaiveFeeModal
        waiveModal={waiveModal}
        waiveReason={waiveReason}
        setWaiveReason={setWaiveReason}
        onWaive={handleWaiveFee}
        onClose={() => { setWaiveModal(null); setWaiveReason(''); }}
        processing={processingFee}
      />

      <InstallmentModal
        installmentModal={installmentModal}
        installmentMonths={installmentMonths}
        setInstallmentMonths={setInstallmentMonths}
        onSetup={handleSetupInstallment}
        onClose={() => setInstallmentModal(null)}
        processing={processingFee}
      />

      <ManualFeeModal
        isOpen={manualFeeModal}
        staffList={staffList}
        staffId={manualFeeStaffId}
        setStaffId={setManualFeeStaffId}
        amount={manualFeeAmount}
        setAmount={setManualFeeAmount}
        reason={manualFeeReason}
        setReason={setManualFeeReason}
        thbRate={thbRate}
        idrRate={idrRate}
        onAdd={handleAddManualFee}
        onClose={() => { setManualFeeModal(false); setManualFeeStaffId(''); setManualFeeAmount(''); setManualFeeReason(''); }}
        processing={processingFee}
      />

      <PaymentModal
        paymentModal={paymentModal}
        paymentAmount={paymentAmount}
        setPaymentAmount={setPaymentAmount}
        paymentCurrency={paymentCurrency}
        setPaymentCurrency={setPaymentCurrency}
        paymentNote={paymentNote}
        setPaymentNote={setPaymentNote}
        thbRate={thbRate}
        idrRate={idrRate}
        formatCurrency={formatCurrency}
        onRecord={handleRecordPartialPayment}
        onClose={() => { setPaymentModal(null); setPaymentAmount(''); setPaymentCurrency('USD'); setPaymentNote(''); }}
        processing={processingFee}
      />

      <CurrencyModal
        isOpen={currencyModal}
        thbRate={thbRate}
        setThbRate={setThbRate}
        idrRate={idrRate}
        setIdrRate={setIdrRate}
        onSave={handleUpdateCurrencyRates}
        onClose={() => setCurrencyModal(false)}
        processing={processingFee}
      />
    </div>
  );
}
