import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, FreqData, Meta } from "./api";

interface Store {
  meta: Meta | null;
  setMeta: (m: Meta) => void;
  freq: string;
  setFreq: (f: string) => void;
  period: string;          // selected as-of period (latest by default)
  setPeriod: (p: string) => void;
  data: FreqData | null;
  loading: boolean;
  running: boolean;
  error: string | null;
  toast: { msg: string; error?: boolean } | null;
  showToast: (msg: string, error?: boolean) => void;
  refresh: (fresh?: boolean) => Promise<void>;
}

const Ctx = createContext<Store>(null as any);
export const useStore = () => useContext(Ctx);

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [freq, setFreqState] = useState<string>("quarterly");
  const [period, setPeriod] = useState<string>("");
  const [data, setData] = useState<FreqData | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; error?: boolean } | null>(null);

  const showToast = useCallback((msg: string, error = false) => {
    setToast({ msg, error });
    setTimeout(() => setToast(null), 3500);
  }, []);

  const loadData = useCallback(async (f: string, allowAutoRun = true) => {
    setLoading(true);
    setError(null);
    try {
      const d = await api.data(f);
      setData(d);
      setPeriod(d?.periods?.latest || "");
    } catch (e: any) {
      // Not exported yet -> trigger a run once if allowed.
      if (e?.response?.status === 404 && allowAutoRun) {
        setRunning(true);
        try {
          const res = await api.run(f);
          if (res && res.data && !res.data.empty) {
            setData(res.data);
            setPeriod(res.data?.periods?.latest || "");
          } else {
            setError(`Chưa có dữ liệu cho tần suất '${f}'. Vui lòng nhấn nút 'Chạy lại'.`);
          }
        } catch (err: any) {
          setError(err?.response?.data?.error || String(err));
        } finally {
          setRunning(false);
        }
      } else {
        setError(e?.response?.data?.error || String(e));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    api.meta().then((m) => {
      setMeta(m);
      const freqs = (m && Array.isArray(m.frequencies) && m.frequencies.length > 0)
        ? m.frequencies
        : ["combined", "monthly", "quarterly", "yearly", "daily"];
      // Default to the integrated multi-frequency view when available.
      const initial = freqs.includes("combined") ? "combined"
        : freqs.includes("monthly") ? "monthly"
        : freqs[0] || "quarterly";
      setFreqState(initial);
      loadData(initial);
    }).catch((e) => { setError(String(e)); setLoading(false); });
  }, [loadData]);

  const setFreq = useCallback((f: string) => {
    setFreqState(f);
    loadData(f);
  }, [loadData]);

  const refresh = useCallback(async (fresh = false) => {
    setRunning(true);
    showToast(`Đang chạy lại pipeline (${freq})...`);
    try {
      const res = await api.run(freq, fresh);
      const payload = (res && res.data && !res.data.empty) ? res.data : (res && !res.empty) ? res : null;
      if (payload && (payload.rule_findings || payload.anomalies || payload.summary)) {
        setData(payload);
        setPeriod(payload?.periods?.latest || "");
      } else {
        await loadData(freq);
      }
      showToast("Đã cập nhật kết quả phân tích.");
    } catch (e: any) {
      showToast(e?.response?.data?.error || "Chạy pipeline thất bại", true);
      await loadData(freq);
    } finally {
      setRunning(false);
    }
  }, [freq, showToast, loadData]);

  return (
    <Ctx.Provider value={{ meta, setMeta, freq, setFreq, period, setPeriod, data, loading, running, error, toast, showToast, refresh }}>
      {children}
    </Ctx.Provider>
  );
}
