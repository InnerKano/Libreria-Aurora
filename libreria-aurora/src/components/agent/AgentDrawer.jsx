import { useState } from "react";
import AgentChat from "./AgentChat";
import AgentStatusPanel from "./AgentStatusPanel";

function AgentDrawer({ isOpen, onClose, topOffset = "12vh" }) {
  const [activeTab, setActiveTab] = useState("chat");
  return (
    <>
      <div
        className={`fixed right-0 z-40 w-[28vw] min-w-[300px] max-w-[420px] transform transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
        style={{ top: topOffset, height: `calc(100vh - ${topOffset})` }}
      >
        <div className="flex h-full flex-col bg-[#F8F9FC] shadow-xl border-l border-[#E5E7EB]">
          <div className="flex items-center justify-between px-4 py-3 bg-[#1B2459] text-white">
            <div>
              <p className="text-sm font-semibold">Asistente Aurora</p>
              <p className="text-xs text-[#D9E1FF]">Catálogo y acciones rápidas</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
                  activeTab === "chat"
                    ? "bg-white text-[#1B2459]"
                    : "bg-white/10 text-white"
                }`}
                onClick={() => setActiveTab("chat")}
              >
                Chat
              </button>
              <button
                className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
                  activeTab === "status"
                    ? "bg-white text-[#1B2459]"
                    : "bg-white/10 text-white"
                }`}
                onClick={() => setActiveTab("status")}
              >
                Estado
              </button>
              <button
                className="text-white text-lg"
                onClick={onClose}
                aria-label="Cerrar asistente"
              >
                ×
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-hidden p-4">
            {activeTab === "chat" ? <AgentChat /> : <AgentStatusPanel />}
          </div>
        </div>
      </div>

      {isOpen && (
        <div
          className="fixed right-0 z-30 w-full bg-black/20"
          style={{ top: topOffset, height: `calc(100vh - ${topOffset})` }}
          onClick={onClose}
          aria-hidden
        />
      )}
    </>
  );
}

export default AgentDrawer;
