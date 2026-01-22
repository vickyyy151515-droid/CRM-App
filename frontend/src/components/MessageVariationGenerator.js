/**
 * MessageVariationGenerator - Staff tool to generate unique WhatsApp message variations
 * Helps avoid spam detection by creating natural variations of messages
 */
import { useState } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  MessageSquare, Wand2, Copy, Check, RefreshCw, 
  Sparkles, ChevronDown, ChevronUp, Info, Zap
} from 'lucide-react';

const TEMPLATES = [
  {
    id: 'promo',
    name: 'Promo/Diskon',
    icon: '🎉',
    template: 'Halo kak! Ada promo spesial nih buat kakak. [DETAIL PROMO]. Yuk buruan sebelum kehabisan!'
  },
  {
    id: 'follow_up',
    name: 'Follow Up',
    icon: '📞',
    template: 'Hai kak, aku mau follow up soal [TOPIK] kemarin. Gimana kak, ada yang bisa aku bantu?'
  },
  {
    id: 'greeting',
    name: 'Sapaan Awal',
    icon: '👋',
    template: 'Halo kak! Aku dari [NAMA]. Ada yang bisa aku bantu hari ini?'
  },
  {
    id: 'reminder',
    name: 'Reminder',
    icon: '⏰',
    template: 'Hai kak, friendly reminder nih buat [DETAIL]. Jangan sampai kelewatan ya kak!'
  },
  {
    id: 'thank_you',
    name: 'Terima Kasih',
    icon: '🙏',
    template: 'Makasih banyak kak sudah [AKSI]! Semoga kakak puas ya. Kalau ada apa-apa hubungi aku lagi ya kak'
  }
];

export default function MessageVariationGenerator() {
  const [originalMessage, setOriginalMessage] = useState('');
  const [numVariations, setNumVariations] = useState(5);
  const [variations, setVariations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [showTemplates, setShowTemplates] = useState(false);
  const [showTips, setShowTips] = useState(false);

  const handleGenerate = async () => {
    if (!originalMessage.trim()) {
      toast.error('Tulis pesan dulu ya kak');
      return;
    }

    if (originalMessage.trim().length < 10) {
      toast.error('Pesan terlalu pendek, minimal 10 karakter');
      return;
    }

    setLoading(true);
    setVariations([]);

    try {
      const response = await api.post('/message-variations/generate', {
        original_message: originalMessage,
        num_variations: numVariations
      });

      setVariations(response.data.variations);
      toast.success(`${response.data.count} variasi berhasil dibuat! ✨`);
    } catch (error) {
      console.error('Error generating variations:', error);
      const errorMsg = error.response?.data?.detail || 'Gagal generate variasi';
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async (text, index) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(index);
      toast.success('Pesan berhasil dicopy!');
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (error) {
      toast.error('Gagal copy pesan');
    }
  };

  const handleUseTemplate = (template) => {
    setOriginalMessage(template);
    setShowTemplates(false);
    toast.info('Template dipilih, silakan edit sesuai kebutuhan');
  };

  const handleClear = () => {
    setOriginalMessage('');
    setVariations([]);
  };

  return (
    <div className="space-y-6" data-testid="message-variation-generator">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Sparkles className="text-amber-500" size={28} />
            Variasi Pesan WhatsApp
          </h1>
          <p className="text-slate-600 dark:text-slate-400 mt-1">
            Generate pesan unik untuk hindari deteksi spam & banned
          </p>
        </div>
        <button
          onClick={() => setShowTips(!showTips)}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg transition-colors"
        >
          <Info size={16} />
          Tips
        </button>
      </div>

      {/* Tips Section */}
      {showTips && (
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4">
          <h3 className="font-semibold text-amber-800 dark:text-amber-400 mb-2 flex items-center gap-2">
            <Zap size={18} />
            Tips Menghindari Banned WhatsApp
          </h3>
          <ul className="text-sm text-amber-700 dark:text-amber-300 space-y-1">
            <li>• <strong>Jangan copy-paste</strong> pesan yang sama ke banyak orang</li>
            <li>• <strong>Tunggu 5-10 detik</strong> antara setiap pesan yang dikirim</li>
            <li>• <strong>Variasikan pesan</strong> setiap beberapa kali kirim</li>
            <li>• <strong>Jangan kirim</strong> ke nomor yang belum pernah chat duluan</li>
            <li>• <strong>Gunakan fitur ini</strong> untuk buat variasi natural setiap pesan</li>
          </ul>
        </div>
      )}

      {/* Main Input Section */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
        {/* Templates Toggle */}
        <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
          <button
            onClick={() => setShowTemplates(!showTemplates)}
            className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 hover:text-indigo-600 transition-colors"
          >
            <MessageSquare size={16} />
            Pakai Template
            {showTemplates ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>

        {/* Templates Grid */}
        {showTemplates && (
          <div className="p-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/30">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
              {TEMPLATES.map((template) => (
                <button
                  key={template.id}
                  onClick={() => handleUseTemplate(template.template)}
                  className="p-3 text-left rounded-lg border border-slate-200 dark:border-slate-700 hover:border-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-all"
                >
                  <span className="text-xl">{template.icon}</span>
                  <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mt-1">{template.name}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message Input */}
        <div className="p-4">
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            Pesan Original
          </label>
          <textarea
            value={originalMessage}
            onChange={(e) => setOriginalMessage(e.target.value)}
            placeholder="Tulis pesan yang mau divariasikan di sini...&#10;&#10;Contoh: Halo kak, mau info nih ada promo deposit 50rb bonus 10rb. Berlaku sampai besok aja loh kak. Yuk jangan sampai kelewatan!"
            className="w-full h-32 px-4 py-3 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white placeholder-slate-400 resize-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            data-testid="original-message-input"
          />
          <div className="flex justify-between items-center mt-2 text-xs text-slate-500">
            <span>{originalMessage.length} karakter</span>
            {originalMessage && (
              <button
                onClick={handleClear}
                className="text-red-500 hover:text-red-700"
              >
                Hapus
              </button>
            )}
          </div>
        </div>

        {/* Controls */}
        <div className="px-4 pb-4 flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="text-sm text-slate-600 dark:text-slate-400">Jumlah variasi:</label>
            <select
              value={numVariations}
              onChange={(e) => setNumVariations(parseInt(e.target.value))}
              className="px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm"
              data-testid="num-variations-select"
            >
              {[3, 5, 7, 10].map((num) => (
                <option key={num} value={num}>{num} variasi</option>
              ))}
            </select>
          </div>

          <button
            onClick={handleGenerate}
            disabled={loading || !originalMessage.trim()}
            className="flex-1 md:flex-none flex items-center justify-center gap-2 px-6 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg"
            data-testid="generate-btn"
          >
            {loading ? (
              <>
                <RefreshCw className="animate-spin" size={18} />
                Generating...
              </>
            ) : (
              <>
                <Wand2 size={18} />
                Generate Variasi
              </>
            )}
          </button>
        </div>
      </div>

      {/* Results Section */}
      {variations.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20">
            <h3 className="font-semibold text-emerald-800 dark:text-emerald-400 flex items-center gap-2">
              <Sparkles size={18} />
              {variations.length} Variasi Berhasil Dibuat
            </h3>
            <p className="text-xs text-emerald-600 dark:text-emerald-500 mt-0.5">
              Klik untuk copy, lalu paste ke WhatsApp
            </p>
          </div>

          <div className="divide-y divide-slate-100 dark:divide-slate-700">
            {variations.map((variation, index) => (
              <div
                key={index}
                className="p-4 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors group"
              >
                <div className="flex gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-xs font-bold flex items-center justify-center">
                    {index + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-slate-700 dark:text-slate-300 whitespace-pre-wrap break-words">
                      {variation}
                    </p>
                  </div>
                  <button
                    onClick={() => handleCopy(variation, index)}
                    className={`shrink-0 p-2 rounded-lg transition-all ${
                      copiedIndex === index
                        ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400'
                        : 'bg-slate-100 text-slate-500 hover:bg-indigo-100 hover:text-indigo-600 dark:bg-slate-700 dark:text-slate-400 dark:hover:bg-indigo-900/30 dark:hover:text-indigo-400'
                    }`}
                    title="Copy pesan"
                    data-testid={`copy-btn-${index}`}
                  >
                    {copiedIndex === index ? <Check size={18} /> : <Copy size={18} />}
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Regenerate Button */}
          <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-900/20 rounded-lg transition-colors font-medium"
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
              Generate Ulang Variasi Baru
            </button>
          </div>
        </div>
      )}

      {/* Empty State */}
      {variations.length === 0 && !loading && (
        <div className="text-center py-12 text-slate-500 dark:text-slate-400">
          <MessageSquare size={48} className="mx-auto mb-4 opacity-30" />
          <p>Tulis pesan di atas lalu klik <strong>Generate Variasi</strong></p>
          <p className="text-sm mt-1">Variasi akan muncul di sini</p>
        </div>
      )}
    </div>
  );
}
