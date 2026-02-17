/**
 * Staff Fee Card Component
 * Displays individual staff fee summary with expandable details
 */
import { 
  DollarSign, ChevronDown, ChevronUp, CreditCard, Ban, CheckCircle,
  XCircle, Trash2, Timer 
} from 'lucide-react';

export default function StaffFeeCard({
  staff,
  isExpanded,
  onToggle,
  formatCurrency,
  onRecordPayment,
  onSetupInstallment,
  onCancelInstallment,
  onRecordInstallmentPayment,
  onWaiveFee,
  onRemoveIzinFee,
  onDeleteManualFee,
  onDeletePayment,
  processingFee
}) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
      {/* Staff Header */}
      <div 
        className="p-4 flex justify-between items-center cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/50"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${staff.remaining_fee > 0 ? 'bg-red-100 dark:bg-red-900/30' : 'bg-emerald-100 dark:bg-emerald-900/30'}`}>
            <DollarSign className={staff.remaining_fee > 0 ? 'text-red-600' : 'text-emerald-600'} size={20} />
          </div>
          <div>
            <p className="font-semibold text-slate-900 dark:text-white">{staff.staff_name}</p>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {staff.late_days > 0 && `${staff.late_days} late day(s) • ${staff.total_late_minutes} min`}
              {staff.izin_overage_days > 0 && `${staff.late_days > 0 ? ' • ' : ''}${staff.izin_overage_days} izin overage day(s) • ${staff.total_izin_overage_minutes?.toFixed(1)} min`}
              {staff.manual_fees?.length > 0 && ` • ${staff.manual_fees.length} manual fee(s)`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-sm text-slate-500">Total: {formatCurrency(staff.total_fee, 'USD')}</p>
            {staff.total_paid > 0 && <p className="text-sm text-emerald-600">Paid: {formatCurrency(staff.total_paid, 'USD')}</p>}
            <p className={`text-lg font-bold ${staff.remaining_fee > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
              {staff.remaining_fee > 0 ? `Remaining: ${formatCurrency(staff.remaining_fee, 'USD')}` : '✓ Fully Paid'}
            </p>
            <p className="text-xs text-slate-400">
              {formatCurrency(staff.remaining_fee_thb, 'THB')} • {formatCurrency(staff.remaining_fee_idr, 'IDR')}
            </p>
          </div>
          {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </div>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="border-t border-slate-200 dark:border-slate-700 p-4 bg-slate-50 dark:bg-slate-900/50">
          {/* Action Buttons */}
          <div className="flex flex-wrap gap-2 mb-4">
            {staff.remaining_fee > 0 && (
              <button
                onClick={() => onRecordPayment(staff)}
                className="flex items-center gap-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm"
              >
                <CreditCard size={16} />
                Record Payment
              </button>
            )}
            {!staff.installment && staff.remaining_fee > 0 ? (
              <button
                onClick={() => onSetupInstallment(staff)}
                className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm"
              >
                <CreditCard size={16} />
                Setup Installment
              </button>
            ) : staff.installment && (
              <>
                <button
                  onClick={() => onCancelInstallment(staff.staff_id)}
                  disabled={processingFee === `cancel-installment-${staff.staff_id}`}
                  className="flex items-center gap-1 px-3 py-1.5 bg-gray-600 hover:bg-gray-700 text-white rounded-lg text-sm disabled:opacity-50"
                >
                  <Ban size={16} />
                  Cancel Installment
                </button>
                {/* Payment buttons for each installment month */}
                {[...Array(staff.installment.num_months)].map((_, idx) => {
                  const payMonth = idx + 1;
                  const isPaid = staff.installment.paid_months?.includes(payMonth);
                  return (
                    <button
                      key={payMonth}
                      onClick={() => !isPaid && onRecordInstallmentPayment(staff.staff_id, payMonth)}
                      disabled={isPaid || processingFee === `pay-${staff.staff_id}-${payMonth}`}
                      className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm ${
                        isPaid 
                          ? 'bg-emerald-100 text-emerald-700 cursor-not-allowed' 
                          : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                      }`}
                    >
                      <CheckCircle size={16} />
                      {isPaid ? `Month ${payMonth} Paid` : `Pay Month ${payMonth} ($${staff.installment.monthly_amount.toFixed(2)})`}
                    </button>
                  );
                })}
              </>
            )}
          </div>

          {/* Late Records Table */}
          {staff.records.length > 0 && (
            <LateRecordsTable 
              records={staff.records} 
              onWaive={onWaiveFee}
              staffId={staff.staff_id}
              staffName={staff.staff_name}
            />
          )}

          {/* Izin Overage Records Table */}
          {staff.izin_overage_records?.length > 0 && (
            <IzinOverageTable 
              records={staff.izin_overage_records}
              formatCurrency={formatCurrency}
              onRemove={onRemoveIzinFee}
              staffId={staff.staff_id}
              staffName={staff.staff_name}
              processingFee={processingFee}
            />
          )}

          {/* Manual Fees Table */}
          {staff.manual_fees?.length > 0 && (
            <ManualFeesTable 
              fees={staff.manual_fees}
              onDelete={onDeleteManualFee}
              formatCurrency={formatCurrency}
              processingFee={processingFee}
            />
          )}

          {/* Payments Table */}
          {staff.payments?.length > 0 && (
            <PaymentsTable 
              payments={staff.payments}
              onDelete={onDeletePayment}
              formatCurrency={formatCurrency}
              processingFee={processingFee}
            />
          )}
        </div>
      )}
    </div>
  );
}

function LateRecordsTable({ records, onWaive, staffId, staffName }) {
  return (
    <>
      <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Late Records:</p>
      <div className="overflow-x-auto mb-4">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 dark:bg-slate-800">
            <tr>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Date</th>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Check-in</th>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Late (min)</th>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Fee</th>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
            {records.map((record, idx) => (
              <tr key={idx}>
                <td className="px-3 py-2 text-slate-900 dark:text-white font-mono">{record.date}</td>
                <td className="px-3 py-2 text-slate-600 dark:text-slate-300 font-mono">{record.check_in_time}</td>
                <td className="px-3 py-2 text-amber-600 font-medium">{record.late_minutes}</td>
                <td className="px-3 py-2 text-red-600 font-medium">${record.fee}</td>
                <td className="px-3 py-2">
                  <button
                    onClick={() => onWaive({ staffId, date: record.date, staffName, fee: record.fee })}
                    className="flex items-center gap-1 px-2 py-1 bg-gray-100 hover:bg-gray-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-gray-700 dark:text-slate-300 rounded text-xs"
                  >
                    <XCircle size={14} />
                    Waive
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function ManualFeesTable({ fees, onDelete, formatCurrency, processingFee }) {
  return (
    <>
      <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Manual Fees:</p>
      <div className="overflow-x-auto mb-4">
        <table className="w-full text-sm">
          <thead className="bg-amber-50 dark:bg-amber-900/20">
            <tr>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Date</th>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Amount</th>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Reason</th>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Added By</th>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
            {fees.map((mf, idx) => (
              <tr key={idx}>
                <td className="px-3 py-2 text-slate-900 dark:text-white font-mono">{mf.date}</td>
                <td className="px-3 py-2 text-red-600 font-medium">{formatCurrency(mf.amount_usd, 'USD')}</td>
                <td className="px-3 py-2 text-slate-600 dark:text-slate-300">{mf.reason}</td>
                <td className="px-3 py-2 text-slate-500 dark:text-slate-400">{mf.added_by}</td>
                <td className="px-3 py-2">
                  <button
                    onClick={() => onDelete(mf.id)}
                    disabled={processingFee === `delete-manual-${mf.id}`}
                    className="flex items-center gap-1 px-2 py-1 bg-red-100 hover:bg-red-200 dark:bg-red-900/30 dark:hover:bg-red-900/50 text-red-700 dark:text-red-400 rounded text-xs disabled:opacity-50"
                  >
                    <Trash2 size={14} />
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function PaymentsTable({ payments, onDelete, formatCurrency, processingFee }) {
  return (
    <>
      <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Payments Received:</p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-emerald-50 dark:bg-emerald-900/20">
            <tr>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Date</th>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Amount (Original)</th>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Amount (USD)</th>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Note</th>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
            {payments.map((p, idx) => (
              <tr key={idx}>
                <td className="px-3 py-2 text-slate-900 dark:text-white font-mono">{p.date?.split('T')[0]}</td>
                <td className="px-3 py-2 text-emerald-600 font-medium">
                  {p.original_currency === 'USD' ? formatCurrency(p.original_amount, 'USD') :
                   p.original_currency === 'THB' ? formatCurrency(p.original_amount, 'THB') :
                   formatCurrency(p.original_amount, 'IDR')}
                </td>
                <td className="px-3 py-2 text-slate-600 dark:text-slate-300">{formatCurrency(p.amount_usd, 'USD')}</td>
                <td className="px-3 py-2 text-slate-500 dark:text-slate-400">{p.note || '-'}</td>
                <td className="px-3 py-2">
                  <button
                    onClick={() => onDelete(p.id)}
                    disabled={processingFee === `delete-payment-${p.id}`}
                    className="flex items-center gap-1 px-2 py-1 bg-red-100 hover:bg-red-200 dark:bg-red-900/30 dark:hover:bg-red-900/50 text-red-700 dark:text-red-400 rounded text-xs disabled:opacity-50"
                  >
                    <Trash2 size={14} />
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function IzinOverageTable({ records, formatCurrency }) {
  return (
    <>
      <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-1.5">
        <Timer size={14} className="text-orange-500" />
        Izin Overage Fees (over 30 min daily limit):
      </p>
      <div className="overflow-x-auto mb-4">
        <table className="w-full text-sm" data-testid="izin-overage-table">
          <thead className="bg-orange-50 dark:bg-orange-900/20">
            <tr>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Date</th>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Total Izin</th>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Overage</th>
              <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Fee</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
            {records.map((record, idx) => (
              <tr key={idx}>
                <td className="px-3 py-2 text-slate-900 dark:text-white font-mono">{record.date}</td>
                <td className="px-3 py-2 text-slate-600 dark:text-slate-300">{record.total_izin_minutes?.toFixed(1)} min</td>
                <td className="px-3 py-2 text-orange-600 font-medium">+{record.overage_minutes?.toFixed(1)} min</td>
                <td className="px-3 py-2 text-red-600 font-medium">{formatCurrency(record.fee, 'USD')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
