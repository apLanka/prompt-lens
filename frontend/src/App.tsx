import { Link, Outlet } from "react-router-dom";

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <Link to="/" className="app-title">PromptLens</Link>
        <span className="app-subtitle">Prompt regression testing</span>
      </header>
      <main className="app-main"><Outlet /></main>
    </div>
  );
}
