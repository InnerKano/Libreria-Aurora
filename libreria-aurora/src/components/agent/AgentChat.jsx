import { useState } from "react";
import { getApiUrl } from "../../api/config";

const DEFAULT_K = 5;

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

function AgentChat({ onAction }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hola 👋 Soy tu asistente del catálogo. ¿Qué libro buscas?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [orderId, setOrderId] = useState("");

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
      const response = await fetch(getApiUrl("/api/agent/"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: text,
          k: DEFAULT_K,
          prefer_vector: true,
          trace: false,
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
    const token = localStorage.getItem("token");
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
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-4 pr-2">
        {messages.map((msg, index) => {
          const isUser = msg.role === "user";
          const results = (msg.results || []).map(normalizeResult).filter((item) => item.titulo);

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

              {!isUser && results.length > 0 && (
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
      </div>

      <div className="mt-4 flex flex-col gap-2">
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
            const hasToken = !!localStorage.getItem("token");
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
