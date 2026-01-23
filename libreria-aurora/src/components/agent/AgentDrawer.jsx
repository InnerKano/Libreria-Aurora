import AgentChat from "./AgentChat";

function AgentDrawer({ isOpen, onClose, topOffset = "12vh" }) {
  return (
    <>
      <div
        className={`fixed left-0 z-40 w-[28vw] min-w-[300px] max-w-[420px] transform transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        style={{ top: topOffset, height: `calc(100vh - ${topOffset})` }}
      >
        <div className="flex h-full flex-col bg-[#F8F9FC] shadow-xl border-r border-[#E5E7EB]">
          <div className="flex items-center justify-between px-4 py-3 bg-[#1B2459] text-white">
            <div>
              <p className="text-sm font-semibold">Asistente Aurora</p>
              <p className="text-xs text-[#D9E1FF]">Catálogo y acciones rápidas</p>
            </div>
            <button
              className="text-white text-lg"
              onClick={onClose}
              aria-label="Cerrar asistente"
            >
              ×
            </button>
          </div>
          <div className="flex-1 overflow-hidden p-4">
            <AgentChat />
          </div>
        </div>
      </div>

      {isOpen && (
        <div
          className="fixed left-0 z-30 w-full bg-black/20"
          style={{ top: topOffset, height: `calc(100vh - ${topOffset})` }}
          onClick={onClose}
          aria-hidden
        />
      )}
    </>
  );
}

export default AgentDrawer;
