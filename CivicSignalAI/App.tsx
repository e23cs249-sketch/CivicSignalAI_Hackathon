import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  ArrowRight, ShieldCheck, Eye, EyeOff, Mail, LockKeyhole, UserRound,
  MapPin, Droplets, Zap, Trash2, Construction, Waves, CircleHelp,
  CheckCircle2, Menu, X, Sparkles, Activity, ArrowUpRight
} from "lucide-react";

type View = "home" | "report" | "track" | "about" | "team-login" | "team-signup";

const issueTypes = [
  { name: "Water & drainage", icon: Droplets, tint: "blue" },
  { name: "Road damage", icon: Construction, tint: "orange" },
  { name: "Street lighting", icon: Zap, tint: "violet" },
  { name: "Waste collection", icon: Trash2, tint: "green" },
];

function Brand() {
  return (
    <a href="#home" className="brand" aria-label="CivicSignal AI home">
      <span className="brand-mark"><Activity size={19} strokeWidth={2.5} /></span>
      <span>CivicSignal <b>AI</b></span>
    </a>
  );
}

function Field({ label, placeholder, type = "text", icon: Icon }: {
  label: string; placeholder: string; type?: string; icon?: typeof Mail;
}) {
  const [visible, setVisible] = useState(false);
  const isPassword = type === "password";
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <span className="field-wrap">
        {Icon && <Icon className="field-icon" size={17} />}
        <input type={isPassword ? (visible ? "text" : "password") : type} placeholder={placeholder} required minLength={isPassword ? 8 : undefined} />
        {isPassword && (
          <button className="show-password" type="button" aria-label={visible ? "Hide password" : "Show password"} onClick={() => setVisible(!visible)}>
            {visible ? <EyeOff size={17} /> : <Eye size={17} />}
          </button>
        )}
      </span>
      {isPassword && <small className="field-hint">Use at least 8 characters.</small>}
    </label>
  );
}

function TeamLogin({ onSignup }: { onSignup: () => void }) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setMessage("");
    const form = new FormData(e.currentTarget);
    try {
      // Connect this request to your backend auth endpoint before production.
      const response = await fetch("/api/auth/team/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: form.get("email"), password: form.get("password") }),
      });
      if (!response.ok) throw new Error("Login could not be verified. Check your credentials or contact your administrator.");
      setMessage("Login accepted. Connect your protected dashboard route here.");
    } catch (err) {
      setMessage(err instanceof Error && err.message.includes("Login could not") ? err.message : "Team authentication service is not connected yet. Ask your administrator to configure it.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <motion.section className="auth-panel" key="login" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: .4 }}>
      <div className="auth-kicker"><span className="status-dot" /> AUTHORIZED PERSONNEL</div>
      <h1>Good to have<br /><em>you back.</em></h1>
      <p className="auth-copy">Sign in to review civic reports, coordinate responses, and keep your community moving.</p>
      <form className="auth-form" onSubmit={submit}>
        <Field label="Work email" placeholder="you@city.gov" type="email" icon={Mail} />
        <Field label="Password" placeholder="Enter your password" type="password" icon={LockKeyhole} />
        <div className="form-meta"><span><ShieldCheck size={14} /> Secure team access</span><a href="mailto:admin@civicsignal.example?subject=Team%20access%20help">Need help?</a></div>
        <button className="primary-button" type="submit" disabled={busy}>{busy ? "Verifying…" : "Sign in to workspace"} <ArrowRight size={17} /></button>
      </form>
      {message && <p className="form-message" role="status">{message}</p>}
      <p className="auth-bottom">Need team access? <button type="button" onClick={onSignup}>Request an invitation <ArrowUpRight size={14} /></button></p>
      <p className="security-note"><LockKeyhole size={13} /> Access is limited to administrator-approved team members.</p>
    </motion.section>
  );
}

function TeamSignup({ onLogin }: { onLogin: () => void }) {
  const [sent, setSent] = useState(false);
  return (
    <motion.section className="auth-panel" key="signup" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: .4 }}>
      <div className="auth-kicker"><span className="status-dot" /> TEAM ACCESS REQUEST</div>
      <h1>Let’s make<br /><em>things better.</em></h1>
      <p className="auth-copy">Request access to the CivicSignal operations workspace. An administrator must approve your account.</p>
      {sent ? (
        <div className="success-card"><CheckCircle2 size={24} /><div><b>Request ready</b><p>This demo form is UI-only. Connect it to an invitation endpoint to send the request securely.</p></div></div>
      ) : (
        <form className="auth-form" onSubmit={(e) => { e.preventDefault(); setSent(true); }}>
          <Field label="Full name" placeholder="Your full name" icon={UserRound} />
          <Field label="Official work email" placeholder="you@city.gov" type="email" icon={Mail} />
          <Field label="Invitation code" placeholder="Provided by your administrator" icon={ShieldCheck} />
          <button className="primary-button" type="submit">Request team access <ArrowRight size={17} /></button>
        </form>
      )}
      <p className="auth-bottom">Already approved? <button type="button" onClick={onLogin}>Log in <ArrowRight size={14} /></button></p>
      <p className="security-note"><ShieldCheck size={13} /> No public self-service admin account creation.</p>
    </motion.section>
  );
}

function HomeContent({ navigate }: { navigate: (view: View) => void }) {
  return (
    <motion.section className="home-panel" key="home" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: .45 }}>
      <div className="hero-eyebrow"><Sparkles size={14} /> SMALL REPORTS. BIGGER CHANGE.</div>
      <h1>Your city.<br /><em>Your signal.</em></h1>
      <p className="home-copy">A clearer way to report local issues, follow progress, and help your community thrive.</p>
      <div className="hero-actions">
        <button className="primary-button" onClick={() => navigate("report")}>Report an issue <ArrowRight size={17} /></button>
        <button className="secondary-button" onClick={() => navigate("track")}>Track a report <MapPin size={16} /></button>
      </div>
      <div className="issue-label">WHAT NEEDS ATTENTION?</div>
      <div className="issue-grid">
        {issueTypes.map(({ name, icon: Icon, tint }) => (
          <button className="issue-card" key={name} onClick={() => navigate("report")}>
            <span className={`issue-icon ${tint}`}><Icon size={19} /></span><span>{name}</span><ArrowUpRight size={14} className="issue-arrow" />
          </button>
        ))}
      </div>
      <div className="citizen-note"><CircleHelp size={16} /><span><b>No citizen account needed.</b> Submit a report and keep the report ID to check its status.</span></div>
    </motion.section>
  );
}

function CitizenForm({ view, navigate }: { view: View; navigate: (view: View) => void }) {
  const [submitted, setSubmitted] = useState(false);
  const [reportId, setReportId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const isTrack = view === "track";
  const title = isTrack ? <>Follow the<br /><em>progress.</em></> : view === "about" ? <>Better cities<br /><em>start here.</em></> : <>Your voice<br /><em>matters here.</em></>;
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault(); setError(""); setLoading(true);
    const data = new FormData(e.currentTarget);
    try {
      const endpoint = isTrack ? `/api/reports/${encodeURIComponent(String(data.get("reportId")))}` : "/api/reports";
      const response = await fetch(endpoint, isTrack ? { method: "GET" } : {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category: data.get("category"), landmark: data.get("landmark"), description: data.get("description") })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "We couldn't complete that request. Please check your details.");
      if (!isTrack) setReportId(String(result.report_id || result.id || ""));
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Service unavailable. Please try again.");
    } finally { setLoading(false); }
  }
  return (
    <motion.section className="auth-panel citizen-panel" key={view} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: .4 }}>
      <div className="auth-kicker"><span className="status-dot" /> CITIZEN SERVICES</div>
      <h1>{title}</h1>
      {view === "about" ? <p className="auth-copy">CivicSignal AI helps residents raise local concerns and gives authorized teams a clearer workflow to respond. We keep reporting simple, transparent, and accessible.</p> :
      <p className="auth-copy">{isTrack ? "Enter the report ID you received when you submitted your issue." : "Tell us what’s happening nearby. You can report an issue without creating an account."}</p>}
      {view !== "about" && (submitted ? (
        <div className="success-card"><CheckCircle2 size={24} /><div><b>{isTrack ? "Report lookup complete" : "Report submitted"}</b><p>{isTrack ? "Your report information has been retrieved from the service." : "Save this ID so you can follow your report."}</p>{reportId && <code>{reportId}</code>}</div></div>
      ) : (
        <form className="auth-form" onSubmit={submit}>
          {isTrack ? <Field label="Report ID" placeholder="Paste your report ID" icon={MapPin} /> : <>
            <label className="field"><span className="field-label">Issue category</span><span className="field-wrap select-wrap"><select name="category" required defaultValue=""><option value="" disabled>Select a category</option><option value="water_leak">Water leak</option><option value="road_damage">Road damage</option><option value="streetlight">Street lighting</option><option value="waste">Waste collection</option><option value="drainage">Drainage</option><option value="other">Other</option></select></span></label>
            <Field label="Nearby landmark" placeholder="Street, junction, or landmark" icon={MapPin} />
            <label className="field"><span className="field-label">Describe the issue</span><textarea name="description" placeholder="What happened? Include useful details…" required minLength={5} rows={3} /></label>
          </>}
          {error && <p className="form-message error-message" role="alert">{error}</p>}
          <button className="primary-button" type="submit" disabled={loading}>{loading ? "Please wait…" : isTrack ? "Find my report" : "Submit report"} <ArrowRight size={17} /></button>
        </form>
      ))}
      <p className="auth-bottom"><button type="button" onClick={() => navigate("home")}>← Back to home</button></p>
    </motion.section>
  );
}

export default function App() {
  const [view, setView] = useState<View>("home");
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = (next: View) => { setView(next); setMenuOpen(false); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const links: { label: string; view: View }[] = [
    { label: "Home", view: "home" }, { label: "Report an Issue", view: "report" },
    { label: "Track a Report", view: "track" }, { label: "About", view: "about" },
  ];
  return (
    <main className="app-shell" id="home">
      <div className="ambient ambient-one" /><div className="ambient ambient-two" />
      <header className="topbar">
        <Brand />
        <button className="mobile-menu" aria-label={menuOpen ? "Close navigation" : "Open navigation"} onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X size={20} /> : <Menu size={20} />}</button>
        <nav className={`nav-links ${menuOpen ? "nav-open" : ""}`} aria-label="Main navigation">
          {links.map(link => <button key={link.view} className={view === link.view ? "nav-link active" : "nav-link"} onClick={() => navigate(link.view)}>{link.label}</button>)}
          <button className="team-nav" onClick={() => navigate("team-login")}><ShieldCheck size={15} /> Team Login</button>
        </nav>
      </header>
      <div className="content-grid">
        <section className="visual-panel" aria-label="CivicSignal city illustration">
          <div className="visual-topline"><span><span className="live-dot" /> COMMUNITY SIGNAL NETWORK</span><span>01 — 04</span></div>
          <div className="visual-copy">
            <p>THE FUTURE OF CIVIC CARE</p>
            <h2>Make your<br />neighbourhood<br /><em>feel heard.</em></h2>
            <span className="visual-sub">One report can start a ripple of change.</span>
          </div>
          <div className="city-scene" aria-hidden="true">
            <div className="city-orbit orbit-a" /><div className="city-orbit orbit-b" />
            <div className="city-globe"><div className="globe-grid" /><div className="globe-land land-one" /><div className="globe-land land-two" /><span className="globe-pin pin-one"><MapPin size={15} /></span><span className="globe-pin pin-two"><Waves size={14} /></span></div>
            <div className="city-ground" />
            <div className="building building-a"><i /><i /><i /><i /><i /><i /></div>
            <div className="building building-b"><i /><i /><i /><i /><i /><i /><i /><i /></div>
            <div className="building building-c"><i /><i /><i /><i /><i /><i /></div>
            <div className="building building-d"><i /><i /><i /><i /></div>
            <div className="route route-a" /><div className="route route-b" />
            <div className="floating-chip chip-a"><span className="chip-icon blue"><Droplets size={14} /></span><span><b>Water leak</b><small>Report received</small></span><span className="chip-status">NEW</span></div>
            <div className="floating-chip chip-b"><span className="chip-icon green"><CheckCircle2 size={14} /></span><span><b>Street lighting</b><small>Issue resolved</small></span><span className="chip-check"><CheckCircle2 size={15} /></span></div>
          </div>
          <div className="visual-footer"><span><span className="footer-pulse" /> DESIGNED FOR EVERY CITIZEN</span><span>COMMUNITY FIRST <ArrowUpRight size={13} /></span></div>
        </section>
        <section className="right-panel">
          <AnimatePresence mode="wait">
            {view === "home" ? <HomeContent navigate={navigate} /> :
              view === "team-login" ? <TeamLogin onSignup={() => navigate("team-signup")} /> :
              view === "team-signup" ? <TeamSignup onLogin={() => navigate("team-login")} /> :
              <CitizenForm view={view} navigate={navigate} />}
          </AnimatePresence>
          <footer className="page-footer"><span>© 2026 CivicSignal AI</span><span>Built for communities, with care <span className="footer-heart">♥</span></span></footer>
        </section>
      </div>
    </main>
  );
}
