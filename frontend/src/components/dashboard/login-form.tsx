"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Mode = "login" | "register" | "request-access" | "reset-password";

interface LoginFormProps {
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (email: string, password: string, displayName: string, inviteCode: string) => Promise<void>;
  onRequestAccess?: (email: string, displayName: string, reason: string) => Promise<{ message: string }>;
  onResetPassword?: (email: string) => Promise<{ message: string }>;
}

export function LoginForm({ onLogin, onRegister, onRequestAccess, onResetPassword }: LoginFormProps) {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      if (mode === "login") {
        await onLogin(email, password);
      } else if (mode === "register") {
        await onRegister(email, password, displayName, inviteCode);
      } else if (mode === "request-access" && onRequestAccess) {
        const res = await onRequestAccess(email, displayName, reason);
        setSuccess(res.message || "Access request submitted. You'll receive an invite once approved.");
      } else if (mode === "reset-password" && onResetPassword) {
        const res = await onResetPassword(email);
        setSuccess(res.message || "If this email exists, a reset link has been sent.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  const titles: Record<Mode, string> = {
    "login": "Sign in to your account",
    "register": "Create your account",
    "request-access": "Request access",
    "reset-password": "Reset your password",
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#09090b]">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl text-center">
            Alpha-Beta Terminal
          </CardTitle>
          <p className="text-zinc-500 text-center text-sm">{titles[mode]}</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Register fields */}
            {mode === "register" && (
              <>
                <Field label="Display Name" value={displayName} onChange={setDisplayName} required />
                <Field label="Invite Code" value={inviteCode} onChange={setInviteCode} placeholder="UUID invite code" required />
              </>
            )}

            {/* Request access fields */}
            {mode === "request-access" && (
              <>
                <Field label="Display Name" value={displayName} onChange={setDisplayName} required />
                <Field label="Email" type="email" value={email} onChange={setEmail} required />
                <div>
                  <label className="text-xs text-zinc-400 block mb-1">Why do you want access?</label>
                  <textarea
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    rows={3}
                    className="w-full rounded-md bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500 resize-none"
                    required
                  />
                </div>
              </>
            )}

            {/* Email/Password for login, register, reset */}
            {mode !== "request-access" && (
              <Field label="Email" type="email" value={email} onChange={setEmail} required />
            )}
            {(mode === "login" || mode === "register") && (
              <Field label="Password" type="password" value={password} onChange={setPassword} required />
            )}

            {/* Reset password only needs email */}
            {mode === "reset-password" && (
              <p className="text-xs text-zinc-500">Enter your email to receive a password reset link.</p>
            )}

            {error && (
              <div className="text-red-400 text-sm bg-red-950/50 rounded-md px-3 py-2">{error}</div>
            )}
            {success && (
              <div className="text-emerald-400 text-sm bg-emerald-950/50 rounded-md px-3 py-2">{success}</div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-md bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold py-2.5 transition-colors"
            >
              {loading
                ? "..."
                : mode === "login" ? "Sign In"
                : mode === "register" ? "Register"
                : mode === "request-access" ? "Submit Request"
                : "Send Reset Link"}
            </button>

            {/* Mode toggles */}
            <div className="flex flex-col items-center gap-1 text-sm text-zinc-500">
              {mode === "login" && (
                <>
                  <button type="button" onClick={() => { setMode("register"); setError(""); setSuccess(""); }} className="text-emerald-400 hover:underline">
                    Have an invite code? Register
                  </button>
                  {onRequestAccess && (
                    <button type="button" onClick={() => { setMode("request-access"); setError(""); setSuccess(""); }} className="text-blue-400 hover:underline">
                      No invite? Request access
                    </button>
                  )}
                  {onResetPassword && (
                    <button type="button" onClick={() => { setMode("reset-password"); setError(""); setSuccess(""); }} className="text-zinc-400 hover:underline">
                      Forgot password?
                    </button>
                  )}
                </>
              )}
              {mode !== "login" && (
                <button type="button" onClick={() => { setMode("login"); setError(""); setSuccess(""); }} className="text-emerald-400 hover:underline">
                  Back to sign in
                </button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

function Field({ label, type = "text", value, onChange, placeholder, required }: {
  label: string; type?: string; value: string; onChange: (v: string) => void; placeholder?: string; required?: boolean;
}) {
  return (
    <div>
      <label className="text-xs text-zinc-400 block mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-md bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
        required={required}
      />
    </div>
  );
}
