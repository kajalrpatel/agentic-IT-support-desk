import { ChevronRight } from "lucide-react";
export function WorkspaceHeader() {
  return (
    <header className="topbar">
      <div>
        <span className="workspace-label">NOVATECH</span>
        <ChevronRight size={14} />
        <span>Support desk</span>
      </div>
    </header>
  );
}
