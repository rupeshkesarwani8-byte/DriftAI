import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { BarChart3, Braces, Folder, GitBranch, LayoutDashboard, LogOut, UserRound, Zap } from "lucide-react";
import Dashboard from "./pages/Dashboard";
import Projects from "./pages/Projects";
import Analyze from "./pages/Analyze";
import AnalysisPage from "./pages/AnalysisPage";
import Functions from "./pages/Functions.jsx";
import ImportGithub from "./pages/ImportGithub.jsx";
import Insights from "./pages/Insights.jsx";
import Account from "./pages/Account.jsx";
import NotFound from "./pages/NotFound.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import ServerBanner from "./components/ServerBanner.jsx";
import Logo from "./components/Logo.jsx";
import HomeStats from "./components/HomeStats.jsx";
import Landing from "./pages/Landing.jsx";
import Auth from "./pages/Auth.jsx";
import { AuthProvider, useAuth } from "./AuthContext";
import "./App.css";
import "./auth.css";
import "./polish.css";
import "./logo.css";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/projects", label: "Projects", icon: Folder },
  { to: "/import", label: "Import", icon: GitBranch },
  { to: "/analyze", label: "Analyze", icon: Zap },
  { to: "/functions", label: "Functions", icon: Braces },
  { to: "/insights", label: "Insights", icon: BarChart3 },
  { to: "/account", label: "Account", icon: UserRound },
];

/** The app itself (sidebar + pages). Only reachable when logged in. */
function AppShell() {
  const { user, logout } = useAuth();
  return (
    <div className="shell">
      <div className="bg-orb orb-a" />
      <div className="bg-orb orb-b" />

      <aside className="sidebar">
        <div className="brand">
          <Logo />
        </div>
        <nav className="nav">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-user">
          <div className="su-name">{user?.name}</div>
          <div className="su-mail">{user?.email}</div>
          <button onClick={logout}>
            <LogOut size={14} /> Log out
          </button>
        </div>
        <div className="sidebar-foot">v0.12 · MVP</div>
      </aside>

      <main className="content">
        <ServerBanner />
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<><HomeStats /><Dashboard /></>} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/import" element={<ImportGithub />} />
            <Route path="/analyze" element={<Analyze />} />
            <Route path="/analysis/:id" element={<AnalysisPage />} />
            <Route path="/functions" element={<Functions />} />
            <Route path="/insights" element={<Insights />} />
            <Route path="/account" element={<Account />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </ErrorBoundary>
      </main>
    </div>
  );
}

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="boot">Loading...</div>;
  if (!user) return <Navigate to="/welcome" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/welcome" element={<Landing />} />
        <Route path="/login" element={<Auth mode="login" />} />
        <Route path="/signup" element={<Auth mode="signup" />} />
        <Route
          path="/*"
          element={
            <Protected>
              <AppShell />
            </Protected>
          }
        />
      </Routes>
    </AuthProvider>
  );
}