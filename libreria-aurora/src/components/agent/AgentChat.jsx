import { useEffect, useRef, useState } from "react";
import { getApiUrl } from "../../api/config";

const DEFAULT_K = 5;
const LLM_TOGGLE_KEY = "agent_llm_enabled";

const readLlmEnabled = () => {
  if (typeof window === "undefined") return true;
  const raw = localStorage.getItem(LLM_TOGGLE_KEY);
  return raw !== "false";
};

const readAuthToken = () => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
};

const normalizeResult = (item) => {
  if (!item) return {};
  const metadata = item.metadata || {};
  return {
    libro_id: item.libro_id ?? metadata.libro_id ?? item.id ?? null,
    titulo: item.titulo ?? metadata.titulo ?? item.document ?? "",
    autor: item.autor ?? metadata.autor ?? "",
    precio: item.precio ?? metadata.precio ?? null,
    stock: item.stock ?? metadata.stock ?? null,
    isbn: item.isbn ?? metadata.isbn ?? "",
    editorial: item.editorial ?? metadata.editorial ?? "",
  };
};

const INITIAL_GREETING = {
  role: "assistant",
  content: "Hola 👋 Soy tu asistente del catálogo. ¿Qué libro buscas?",
};

function AgentChat({ onAction }) {
  const [messages, setMessages] = useState([
    INITIAL_GREETING,
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [orderId, setOrderId] = useState("");
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const scrollContainerRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    const token = readAuthToken();
    setIsAuthenticated(!!token);
    if (!token) return;

    const loadHistory = async () => {
      setHistoryLoading(true);
      setHistoryError("");
      try {
        const response = await fetch(getApiUrl("/api/agent/history/"), {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.status === 401) {
          if (!cancelled) {
            setHistoryError("Tu sesión expiró. Inicia sesión para ver tu historial.");
          }
          return;
        }

        const data = await response.json();
        if (!response.ok) {
          if (!cancelled) {
            setHistoryError(data?.message || "No se pudo cargar el historial.");
          }
          return;
        }

        const historyMessages = (data?.messages || [])
          .map((msg) => ({
            role: msg.role,
            content: msg.content,
            meta: msg.meta || {},
            results: Array.isArray(msg?.meta?.results) ? msg.meta.results : [],
            actions: Array.isArray(msg?.meta?.actions) ? msg.meta.actions : [],
            fromHistory: true,
          }))
          .filter((msg) => msg.content);

        if (!cancelled && historyMessages.length > 0) {
          setMessages(historyMessages);
        }
      } catch (error) {
        if (!cancelled) {
          setHistoryError("No pude cargar tu historial. Intenta más tarde.");
        }
      } finally {
        if (!cancelled) {
          setHistoryLoading(false);
        }
      }
    };

    loadHistory();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const threshold = 120;
      const distanceFromBottom =
        container.scrollHeight - container.scrollTop - container.clientHeight;
      const atBottom = distanceFromBottom <= threshold;
      setShowScrollButton(!atBottom);
    };

    handleScroll();
    container.addEventListener("scroll", handleScroll);

    return () => {
      container.removeEventListener("scroll", handleScroll);
    };
  }, []);

  useEffect(() => {
    if (!showScrollButton && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, showScrollButton]);

  const appendMessage = (message) => {
    setMessages((prev) => [...prev, message]);
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    appendMessage({ role: "user", content: text });
    setInput("");
    setLoading(true);

    try {
      const token = readAuthToken();
      const saveHistory = !!token;
      const useLlm = readLlmEnabled();
      const response = await fetch(getApiUrl("/api/agent/"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: text,
          k: DEFAULT_K,
          prefer_vector: true,
          use_llm: useLlm,
          trace: false,
          save_history: saveHistory,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        appendMessage({
          role: "assistant",
          content: data?.message || "Ocurrió un error al consultar el agente.",
        });
        return;
      }

      appendMessage({
        role: "assistant",
        content: data.message || "Listo.",
        results: data.results || [],
        actions: data.actions || [],
      });
    } catch (error) {
      appendMessage({
        role: "assistant",
        content: "No pude contactar el agente. Intenta de nuevo.",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const handleAction = async (action, payload) => {
    const token = readAuthToken();
    if (!token) {
      appendMessage({
        role: "assistant",
        content: "Necesitas iniciar sesión para ejecutar acciones.",
      });
      return;
    }

    try {
      const response = await fetch(getApiUrl("/api/agent/actions/"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          action,
          payload,
          trace: false,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        appendMessage({
          role: "assistant",
          content: data?.message || "No se pudo ejecutar la acción.",
        });
        return;
      }

      appendMessage({
        role: "assistant",
        content: data.message || "Acción completada.",
        results: data.results || [],
        actions: data.actions || [],
      });

      if (onAction) {
        onAction(action, data);
      }
    } catch (error) {
      appendMessage({
        role: "assistant",
        content: "No se pudo ejecutar la acción. Intenta nuevamente.",
      });
    }
  };

  return (
    <div className="relative flex h-full flex-col">
      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto space-y-4 pr-2 pb-2">
        {!isAuthenticated && (
          <div className="rounded-xl border border-[#E5E7EB] bg-white px-3 py-2 text-xs text-[#1B2459]">
            Inicia sesión para guardar tu historial de conversación.
          </div>
        )}
        {historyLoading && (
          <div className="rounded-xl border border-[#E5E7EB] bg-white px-3 py-2 text-xs text-[#1B2459]">
            Cargando historial...
          </div>
        )}
        {historyError && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            {historyError}
          </div>
        )}
        {messages.map((msg, index) => {
          const isUser = msg.role === "user";
          const results = (msg.results || []).map(normalizeResult).filter((item) => item.titulo);
          const showHistoryResults = msg.fromHistory && results.length > 0;

          return (
            <div key={`${msg.role}-${index}`} className="space-y-2">
              <div
                className={`max-w-[90%] rounded-xl px-4 py-3 text-sm ${
                  isUser
                    ? "ml-auto bg-[#3B4CBF] text-white"
                    : "mr-auto bg-white text-[#1B2459] shadow"
                }`}
              >
                {msg.content}
              </div>

              {!isUser && showHistoryResults && (
                <div className="rounded-xl border border-[#E5E7EB] bg-white p-3 text-xs text-[#1B2459]">
                  <p className="mb-2 text-[11px] font-semibold uppercase text-gray-500">
                    Libros consultados
                  </p>
                  <ul className="space-y-1">
                    {results.map((item) => (
                      <li key={item.libro_id || item.titulo} className="flex flex-col">
                        <span className="text-sm font-semibold text-[#1B2459]">{item.titulo}</span>
                        {item.autor && (
                          <span className="text-[11px] text-gray-500">{item.autor}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {!isUser && !msg.fromHistory && results.length > 0 && (
                <div className="space-y-3">
                  {results.map((item) => (
                    <div
                      key={item.libro_id || item.titulo}
                      className="rounded-xl border border-[#E5E7EB] bg-white p-3 shadow-sm"
                    >
                      <p className="text-sm font-semibold text-[#1B2459]">{item.titulo}</p>
                      <p className="text-xs text-gray-500">{item.autor || "Autor no disponible"}</p>
                      <div className="mt-2 flex flex-wrap gap-2 text-xs text-gray-600">
                        {item.precio !== null && <span>Precio: ${item.precio}</span>}
                        {item.stock !== null && <span>Stock: {item.stock}</span>}
                        {item.isbn && <span>ISBN: {item.isbn}</span>}
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          className="rounded-lg bg-[#2B388C] px-3 py-1 text-xs text-white"
                          onClick={() => handleAction("add_to_cart", { book_id: item.libro_id, cantidad: 1 })}
                          disabled={!item.libro_id}
                        >
                          Agregar al carrito
                        </button>
                        <button
                          className="rounded-lg bg-[#F0B429] px-3 py-1 text-xs text-white"
                          onClick={() => handleAction("reserve_book", { book_id: item.libro_id, cantidad: 1 })}
                          disabled={!item.libro_id}
                        >
                          Reservar
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
        {showScrollButton && (
          <div className="sticky bottom-3 flex justify-center">
            <button
              type="button"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-[#1B2459] text-white shadow-lg opacity-50"
              onClick={() => bottomRef.current?.scrollIntoView({ behavior: "smooth" })}
              aria-label="Ir al final del chat"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="h-4 w-4"
                aria-hidden="true"
              >
                <path d="M12 5v14" />
                <path d="M7 14l5 5 5-5" />
              </svg>
            </button>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="mt-3 flex flex-col gap-2">
        <textarea
          rows={2}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Escribe tu consulta..."
          className="w-full resize-none rounded-xl border border-[#D1D5DB] bg-white p-3 text-sm text-[#1B2459] focus:outline-none focus:ring-2 focus:ring-[#3B4CBF]"
        />
        <button
          className="self-end rounded-lg bg-[#3B4CBF] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          onClick={handleSend}
          disabled={loading}
        >
          {loading ? "Enviando..." : "Enviar"}
        </button>
        <div className="flex items-center gap-2">
          {(() => {
            const hasToken = !!readAuthToken();
            const parsedOrderId = Number(orderId);
            const canSubmit = hasToken && orderId && !Number.isNaN(parsedOrderId);

            return (
              <>
                <input
                  type="number"
                  value={orderId}
                  onChange={(event) => setOrderId(event.target.value)}
                  placeholder="ID de pedido"
                  className="w-24 rounded-lg border border-[#D1D5DB] bg-white px-2 py-1 text-xs text-[#1B2459]"
                />
                <button
                  className="text-xs text-[#2B388C] underline disabled:opacity-60"
                  onClick={() => handleAction("order_status", { order_id: parsedOrderId })}
                  disabled={!canSubmit}
                >
                  Consultar estado
                </button>
              </>
            );
          })()}
        </div>
      </div>
    </div>
  );
}

export default AgentChat;
