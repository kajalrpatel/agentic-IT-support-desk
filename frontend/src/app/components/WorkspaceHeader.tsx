import { ChevronRight, ShieldCheck } from "lucide-react";
export function WorkspaceHeader() {
  return (
    <header className="topbar">
      <div>
        <span className="workspace-label">NOVATECH</span>
        <ChevronRight size={14} />
        <span>Support desk</span>
      </div>
      <span className="private-label">
        <ShieldCheck size={14} />
        Your employee workspace
      </span>
    </header>
  );
}
