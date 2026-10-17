import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";

const ToastContext = createContext<(message: string) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<{ id: number; text: string } | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const nextId = useRef(1);

  const show = useCallback((text: string) => {
    setToast({ id: nextId.current++, text });
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setToast(null), 2600);
  }, []);

  return (
    <ToastContext.Provider value={show}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-6 z-50 flex justify-center px-4">
        {toast && (
          <div
            key={toast.id}
            className="settle flex items-center gap-2.5 rounded-full bg-ink py-2.5 pr-5 pl-4 text-[13.5px] font-medium text-paper shadow-[var(--shadow-lg)]"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-[#f4e15c]" aria-hidden="true" />
            {toast.text}
          </div>
        )}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);

/** Copy text from inside a click handler; resolves false if the browser refuses. */
export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
