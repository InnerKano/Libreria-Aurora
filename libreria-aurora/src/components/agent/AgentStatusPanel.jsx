import { useCallback, useEffect, useState } from "react";
import { getApiUrl } from "../../api/config";

const STORAGE_KEY = "agent_llm_enabled";

const readLlmEnabled = () => {
  if (typeof window === "undefined") return true;
  const raw = localStorage.getItem(STORAGE_KEY);
  return raw !== "false";
};

const formatValue = (value) => {
  if (typeof value === "boolean") return value ? "Sí" : "No";
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
};

function AgentStatusPanel() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [updatedAt, setUpdatedAt] = useState(null);
  const [llmEnabled, setLlmEnabled] = useState(readLlmEnabled);

  const fetchStatus = useCallback(async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      setStatus(null);
      setError("Necesitas iniciar sesión para ver el estado del agente.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(getApiUrl("/api/agent/status/"), {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        if (response.status === 401) {
          setError("Tu sesión expiró. Inicia sesión nuevamente.");
        } else {
          setError(data?.message || "No se pudo obtener el estado del agente.");
        }
        setStatus(null);
        return;
      }

      const data = await response.json();
      setStatus(data);
      setUpdatedAt(new Date());
    } catch (err) {
      setError("No se pudo contactar el servidor.");
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleToggle = () => {
    const nextValue = !llmEnabled;
    setLlmEnabled(nextValue);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, String(nextValue));
    }
  };

  if (error) {
    return (
      <div className="flex flex-col gap-3 rounded-xl border border-[#E5E7EB] bg-white p-4 text-sm text-[#1B2459]">
        <p>{error}</p>
        <button
          className="self-start rounded-lg bg-[#2B388C] px-3 py-1 text-xs text-white disabled:opacity-60"
          onClick={fetchStatus}
          disabled={loading}
        >
          {loading ? "Actualizando..." : "Reintentar"}
        </button>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="rounded-xl border border-dashed border-[#CBD5F5] bg-[#F4F6FF] p-4 text-sm text-[#2B388C]">
        Cargando estado del agente...
      </div>
    );
  }

  const rateLimits = Object.entries(status?.limits?.rate_limits || {});

  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-[#1B2459]">Estado operativo</p>
          <p className="text-xs text-[#64748B]">
            {updatedAt ? `Actualizado: ${updatedAt.toLocaleTimeString()}` : ""}
          </p>
        </div>
        <button
          className="rounded-lg bg-[#2B388C] px-3 py-1 text-xs text-white disabled:opacity-60"
          onClick={fetchStatus}
          disabled={loading}
        >
          {loading ? "Actualizando..." : "Actualizar"}
        </button>
      </div>

      <section className="rounded-xl border border-[#E5E7EB] bg-white p-4 shadow-sm">
        <p className="text-sm font-semibold text-[#1B2459]">LLM</p>
        <div className="mt-3 flex items-center justify-between rounded-lg border border-[#E5E7EB] bg-[#F8FAFF] px-3 py-2 text-xs text-[#475569]">
          <div>
            <p className="text-sm font-semibold text-[#1B2459]">Usar LLM en respuestas</p>
            <p className="text-xs text-[#64748B]">
              Si lo desactivas, el agente responde en modo degradado.
            </p>
          </div>
          <button
            className={`relative h-6 w-11 rounded-full transition-colors ${
              llmEnabled ? "bg-[#2B388C]" : "bg-[#CBD5F5]"
            }`}
            onClick={handleToggle}
            aria-label="Activar o desactivar LLM"
          >
            <span
              className={`absolute left-1 top-1 h-4 w-4 rounded-full bg-white transition-transform ${
                llmEnabled ? "translate-x-5" : "translate-x-0"
              }`}
            />
          </button>
        </div>
        <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-[#475569]">
          <div>Proveedor</div>
          <div className="text-right">{formatValue(status.llm?.provider)}</div>
          <div>Modelo</div>
          <div className="text-right">{formatValue(status.llm?.model)}</div>
          <div>Base URL</div>
          <div className="text-right">{formatValue(status.llm?.base_url)}</div>
          <div>Disponible</div>
          <div className="text-right">{formatValue(status.llm?.available)}</div>
          <div>Modo</div>
          <div className="text-right">{formatValue(status.llm?.mode)}</div>
          <div>BYO requerido</div>
          <div className="text-right">{formatValue(status.llm?.requires_byo_key)}</div>
          <div>BYO permitido</div>
          <div className="text-right">{formatValue(status.llm?.byo_key_allowed)}</div>
          <div>Key servidor</div>
          <div className="text-right">{formatValue(status.llm?.server_key_configured)}</div>
          <div>Timeout (s)</div>
          <div className="text-right">{formatValue(status.llm?.timeout_sec)}</div>
          <div>Max tokens</div>
          <div className="text-right">{formatValue(status.llm?.max_tokens)}</div>
        </div>
      </section>

      <section className="rounded-xl border border-[#E5E7EB] bg-white p-4 shadow-sm">
        <p className="text-sm font-semibold text-[#1B2459]">Retrieval</p>
        <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-[#475569]">
          <div>Vector listo</div>
          <div className="text-right">{formatValue(status.retrieval?.vector_ready)}</div>
          <div>Colección</div>
          <div className="text-right">{formatValue(status.retrieval?.collection)}</div>
          <div>Embeddings</div>
          <div className="text-right">{formatValue(status.retrieval?.embedding_model)}</div>
          <div>Normaliza</div>
          <div className="text-right">{formatValue(status.retrieval?.normalize_embeddings)}</div>
        </div>
      </section>

      <section className="rounded-xl border border-[#E5E7EB] bg-white p-4 shadow-sm">
        <p className="text-sm font-semibold text-[#1B2459]">Tools</p>
        <div className="mt-2 text-xs text-[#475569]">
          <p className="font-semibold text-[#1B2459]">Read-only</p>
          <div className="mt-1 flex flex-wrap gap-2">
            {(status.tools?.read_only || []).map((tool) => (
              <span key={tool} className="rounded-full bg-[#E8ECFF] px-2 py-0.5 text-[11px]">
                {tool}
              </span>
            ))}
          </div>
          <p className="mt-3 font-semibold text-[#1B2459]">Acciones</p>
          <div className="mt-1 flex flex-wrap gap-2">
            {(status.tools?.actions || []).map((tool) => (
              <span key={tool} className="rounded-full bg-[#FCEFC7] px-2 py-0.5 text-[11px]">
                {tool}
              </span>
            ))}
          </div>
          <p className="mt-2">
            Requiere auth: <span className="font-semibold">{formatValue(status.tools?.actions_requires_auth)}</span>
          </p>
        </div>
      </section>

      <section className="rounded-xl border border-[#E5E7EB] bg-white p-4 shadow-sm">
        <p className="text-sm font-semibold text-[#1B2459]">Límites</p>
        {rateLimits.length === 0 ? (
          <p className="mt-2 text-xs text-[#64748B]">Sin límites configurados.</p>
        ) : (
          <div className="mt-2 space-y-2 text-xs text-[#475569]">
            {rateLimits.map(([key, value]) => (
              <div key={key} className="flex items-center justify-between">
                <span>{key}</span>
                <span className="font-semibold text-[#1B2459]">{value}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default AgentStatusPanel;
