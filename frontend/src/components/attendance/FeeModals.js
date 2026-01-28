/**
 * Fee-related modals for the Attendance Admin page
 * - WaiveFeeModal: Waive a late fee for a specific date
 * - InstallmentModal: Set up installment plan
 * - ManualFeeModal: Add manual fee
 * - PaymentModal: Record payment
 * - CurrencyModal: Update currency exchange rates
 */
import { CheckCircle } from 'lucide-react';

export function WaiveFeeModal({ 
  waiveModal, 
  waiveReason, 
  setWaiveReason, 
  onWaive, 
  onClose, 
  processing 
}) {
  if (!waiveModal) return null;

  const isProcessing = processing === `${waiveModal.staffId}-${waiveModal.date}`;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 max-w-md w-full mx-4">
        <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Waive Fee</h3>
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
          Waive ${waiveModal.fee} fee for <strong>{waiveModal.staffName}</strong> on {waiveModal.date}?
        </p>
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Reason for waiving <span className="text-red-500">*</span>
          </label>
          <textarea
            value={waiveReason}
            onChange={(e) => setWaiveReason(e.target.value)}
            placeholder="e.g., Emergency situation, system error, etc."
            className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
            rows={3}
          />
        </div>
        <div className="flex gap-2 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-600"
          >
            Cancel
          </button>
          <button
            onClick={() => onWaive(waiveModal.staffId, waiveModal.date)}
            disabled={isProcessing}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
          >
            {isProcessing ? 'Processing...' : 'Waive Fee'}
          </button>
        </div>
      </div>
    </div>
  );
}

export function InstallmentModal({
  installmentModal,
  installmentMonths,
  setInstallmentMonths,
  onSetup,
  onClose,
  processing
}) {
  if (!installmentModal) return null;

  const isProcessing = processing === `installment-${installmentModal.staff_id}`;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 max-w-md w-full mx-4">
        <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Setup Installment Plan</h3>
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
          Total fee for <strong>{installmentModal.staff_name}</strong>: <span className="text-red-600 font-bold">${installmentModal.total_fee}</span>
        </p>
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Number of Months (max 2)
          </label>
          <select
            value={installmentMonths}
            onChange={(e) => setInstallmentMonths(Number(e.target.value))}
            className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
          >
            <option value={1}>1 month (${installmentModal.total_fee.toFixed(2)})</option>
            <option value={2}>2 months (${(installmentModal.total_fee / 2).toFixed(2)}/month)</option>
          </select>
        </div>
        <div className="bg-blue-50 dark:bg-blue-900/30 rounded-lg p-3 mb-4">
          <p className="text-sm text-blue-700 dark:text-blue-300">
            Monthly payment: <strong>${(installmentModal.total_fee / installmentMonths).toFixed(2)}</strong>
          </p>
        </div>
        <div className="flex gap-2 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-600"
          >
            Cancel
          </button>
          <button
            onClick={() => onSetup(installmentModal.staff_id)}
            disabled={isProcessing}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {isProcessing ? 'Processing...' : 'Create Plan'}
          </button>
        </div>
      </div>
    </div>
  );
}

export function ManualFeeModal({
  isOpen,
  staffList,
  staffId,
  setStaffId,
  amount,
  setAmount,
  reason,
  setReason,
  thbRate,
  idrRate,
  onAdd,
  onClose,
  processing
}) {
  if (!isOpen) return null;

  const isProcessing = processing === 'manual-fee';

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 max-w-md w-full mx-4">
        <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Add Manual Fee</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Staff <span className="text-red-500">*</span>
            </label>
            <select
              value={staffId}
              onChange={(e) => setStaffId(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
            >
              <option value="">Select staff...</option>
              {staffList.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Amount (USD) <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="e.g., 50"
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
            />
            {amount && (
              <p className="text-xs text-slate-500 mt-1">
                = ฿{(parseFloat(amount) * thbRate).toLocaleString()} THB = Rp {(parseFloat(amount) * idrRate).toLocaleString()} IDR
              </p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Reason <span className="text-red-500">*</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g., Missed shift, policy violation, etc."
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
              rows={2}
            />
          </div>
        </div>
        <div className="flex gap-2 justify-end mt-4">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-600"
          >
            Cancel
          </button>
          <button
            onClick={onAdd}
            disabled={isProcessing}
            className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50"
          >
            {isProcessing ? 'Adding...' : 'Add Fee'}
          </button>
        </div>
      </div>
    </div>
  );
}

export function PaymentModal({
  paymentModal,
  paymentAmount,
  setPaymentAmount,
  paymentCurrency,
  setPaymentCurrency,
  paymentNote,
  setPaymentNote,
  thbRate,
  idrRate,
  formatCurrency,
  onRecord,
  onClose,
  processing
}) {
  if (!paymentModal) return null;

  const isProcessing = processing === `partial-payment-${paymentModal.staff_id}`;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 max-w-md w-full mx-4">
        <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Record Payment</h3>
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
          Recording payment for <strong>{paymentModal.staff_name}</strong>
          <br />
          <span className="text-red-600">Remaining: {formatCurrency(paymentModal.remaining_fee, 'USD')} = {formatCurrency(paymentModal.remaining_fee_thb, 'THB')} = {formatCurrency(paymentModal.remaining_fee_idr, 'IDR')}</span>
        </p>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Currency
            </label>
            <select
              value={paymentCurrency}
              onChange={(e) => setPaymentCurrency(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
            >
              <option value="USD">USD ($)</option>
              <option value="THB">THB (฿)</option>
              <option value="IDR">IDR (Rp)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Amount <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              step={paymentCurrency === 'USD' ? '0.01' : '1'}
              value={paymentAmount}
              onChange={(e) => setPaymentAmount(e.target.value)}
              placeholder={paymentCurrency === 'USD' ? 'e.g., 50.00' : paymentCurrency === 'THB' ? 'e.g., 155000' : 'e.g., 835000'}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
            />
            {paymentAmount && (
              <p className="text-xs text-emerald-600 mt-1">
                {paymentCurrency !== 'USD' && `= ${formatCurrency(parseFloat(paymentAmount) / (paymentCurrency === 'THB' ? thbRate : idrRate), 'USD')}`}
                {paymentCurrency === 'USD' && `= ${formatCurrency(parseFloat(paymentAmount) * thbRate, 'THB')} = ${formatCurrency(parseFloat(paymentAmount) * idrRate, 'IDR')}`}
              </p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Note (optional)
            </label>
            <input
              type="text"
              value={paymentNote}
              onChange={(e) => setPaymentNote(e.target.value)}
              placeholder="e.g., Cash payment, bank transfer, etc."
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
            />
          </div>
        </div>
        <div className="flex gap-2 justify-end mt-4">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-600"
          >
            Cancel
          </button>
          <button
            onClick={onRecord}
            disabled={isProcessing}
            className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50"
          >
            {isProcessing ? 'Recording...' : 'Record Payment'}
          </button>
        </div>
      </div>
    </div>
  );
}

export function CurrencyModal({
  isOpen,
  thbRate,
  setThbRate,
  idrRate,
  setIdrRate,
  onSave,
  onClose,
  processing
}) {
  if (!isOpen) return null;

  const isProcessing = processing === 'currency-rates';

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 max-w-md w-full mx-4">
        <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Currency Rates</h3>
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
          Set exchange rates relative to $1 USD
        </p>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              $1 USD = THB (฿)
            </label>
            <input
              type="number"
              step="1"
              value={thbRate}
              onChange={(e) => setThbRate(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              $1 USD = IDR (Rp)
            </label>
            <input
              type="number"
              step="1"
              value={idrRate}
              onChange={(e) => setIdrRate(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
            />
          </div>
        </div>
        <div className="flex gap-2 justify-end mt-4">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-600"
          >
            Cancel
          </button>
          <button
            onClick={onSave}
            disabled={isProcessing}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {isProcessing ? 'Saving...' : 'Save Rates'}
          </button>
        </div>
      </div>
    </div>
  );
}
