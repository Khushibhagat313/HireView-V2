import { useState } from "react";
import { api, ApiError, messageFor, setAccessCode } from "../lib/api";
import { ArrowRight, BrandMark } from "./Icons";

/** Temporary shared password until real login exists. The backend enforces it; this screen only collects it. */
export function AccessGate({ onUnlocked }: { onUnlocked: () => void }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  const submit = async () => {
    setChecking(true);
    setError(null);
    setAccessCode(code.trim());
    try {
      await api.resumes(); // any protected call proves the code
      onUnlocked();
    } catch (err) {
      setAccessCode("");
      setError(err instanceof ApiError && err.status === 401 ? "That code isn't right. Check it and try again." : messageFor(err));
    } finally {
      setChecking(false);
    }
  };

  return (
    <main className="mx-auto grid min-h-screen max-w-[440px] content-center gap-8 px-5 py-12">
      <div className="settle grid justify-items-center gap-4 text-center">
        <BrandMark size={48} />
        <div className="grid gap-2">
          <h1 className="font-serif text-[32px] leading-tight font-semibold tracking-[-0.02em]">
            Welcome to <span className="hl-title">HireView</span>
          </h1>
          <p className="text-pencil">This preview is private while login is being built. Enter the access code you were given.</p>
        </div>
      </div>
      <form
        className="sheet sheet-raised settle grid gap-4 p-6"
        style={{ ["--d" as string]: "100ms" }}
        onSubmit={(e) => {
          e.preventDefault();
          if (code.trim() && !checking) submit();
        }}
      >
        <div className="grid gap-2">
          <label htmlFor="code" className="text-[13px] font-medium">
            Access code
          </label>
          <input
            id="code"
            className="field h-11"
            type="password"
            autoComplete="current-password"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            aria-invalid={error ? true : undefined}
            autoFocus
          />
        </div>
        <button type="submit" className="btn h-11 w-full" disabled={!code.trim() || checking}>
          {checking ? "Checking…" : "Continue"}
          {!checking && <ArrowRight size={15} />}
        </button>
        {error && (
          <p className="text-center text-sm text-red" role="alert">
            {error}
          </p>
        )}
      </form>
    </main>
  );
}
