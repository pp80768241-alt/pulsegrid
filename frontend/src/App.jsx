import React, { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import ReplicaBadge from "./components/ReplicaBadge.jsx";
import NotificationPanel from "./components/NotificationPanel.jsx";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8080";
const WS_BASE = import.meta.env.VITE_WS_BASE || "ws://localhost:8080";

export default function App() {
  const [room, setRoom] = useState("general");
  const [sender, setSender] = useState(() => `guest-${Math.floor(Math.random() * 900 + 100)}`);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [connected, setConnected] = useState(false);
  const [notifRecipient, setNotifRecipient] = useState("");
  const [notifTitle, setNotifTitle] = useState("");
  const [notifications, setNotifications] = useState([]);
  const wsRef = useRef(null);
  const scrollRef = useRef(null);

  const loadHistory = useCallback(async (r) => {
    try {
      const res = await axios.get(`${API_BASE}/api/rooms/${r}/history`);
      setMessages(res.data);
    } catch (err) {
      console.error("history load failed", err);
    }
  }, []);

  const refreshNotifications = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/notifications`);
      setNotifications(res.data);
    } catch (err) {
      console.error("notification load failed", err);
    }
  }, []);

  useEffect(() => {
    loadHistory(room);
    refreshNotifications();

    const ws = new WebSocket(`${WS_BASE}/ws/${room}?sender=${encodeURIComponent(sender)}`);
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      setMessages((prev) => [...prev, payload]);
    };
    wsRef.current = ws;

    const poll = setInterval(refreshNotifications, 4000);

    return () => {
      ws.close();
      clearInterval(poll);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [room]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  function sendMessage() {
    const trimmed = draft.trim();
    if (!trimmed || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ content: trimmed }));
    setDraft("");
  }

  async function sendNotification() {
    if (!notifRecipient.trim() || !notifTitle.trim()) return;
    try {
      await axios.post(`${API_BASE}/api/notifications`, {
        recipient: notifRecipient,
        title: notifTitle,
        body: `Triggered from the PulseGrid demo UI in room "${room}".`,
      });
      setNotifTitle("");
      refreshNotifications();
    } catch (err) {
      console.error("notification send failed", err);
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-node" />
          <span>PULSEGRID</span>
        </div>
        <div className={`conn-status ${connected ? "conn-online" : "conn-offline"}`}>
          <span className="conn-dot" />
          {connected ? "connected" : "reconnecting…"}
        </div>
      </header>

      <main className="layout">
        <section className="chat-panel">
          <div className="chat-controls">
            <label>
              <span className="field-label">Room</span>
              <select value={room} onChange={(e) => setRoom(e.target.value)}>
                <option value="general">#general</option>
                <option value="engineering">#engineering</option>
                <option value="ops">#ops</option>
              </select>
            </label>
            <label>
              <span className="field-label">You are</span>
              <input
                type="text"
                value={sender}
                onChange={(e) => setSender(e.target.value)}
              />
            </label>
          </div>

          <div className="message-list" ref={scrollRef}>
            {messages.map((m, i) => (
              <div key={m.id ?? i} className="message-row">
                <div className="message-head">
                  <span className="message-sender mono">{m.sender}</span>
                  <ReplicaBadge instanceId={m.handled_by} />
                </div>
                <div className="message-content">{m.content}</div>
              </div>
            ))}
            {messages.length === 0 && (
              <div className="empty-state">No messages yet in #{room} — say something below.</div>
            )}
          </div>

          <div className="composer">
            <input
              type="text"
              placeholder={`Message #${room}...`}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            />
            <button className="primary-btn" onClick={sendMessage}>Send</button>
          </div>
        </section>

        <section className="side-panel">
          <div className="panel">
            <div className="tag-title">Trigger an async notification</div>
            <div className="notif-form">
              <input
                type="text"
                placeholder="Recipient (e.g. alice@company.com)"
                value={notifRecipient}
                onChange={(e) => setNotifRecipient(e.target.value)}
              />
              <input
                type="text"
                placeholder="Title (e.g. Deploy finished)"
                value={notifTitle}
                onChange={(e) => setNotifTitle(e.target.value)}
              />
              <button className="primary-btn" onClick={sendNotification}>Enqueue</button>
            </div>
            <p className="hint">
              This hits <span className="mono">POST /api/notifications</span>, returns instantly, and a
              separate worker process delivers it asynchronously off a Redis queue.
            </p>
          </div>

          <NotificationPanel notifications={notifications} onRefresh={refreshNotifications} />
        </section>
      </main>

      <footer className="footer">
        <span>PULSEGRID · FastAPI + Redis Pub/Sub + PostgreSQL · 2 API replicas behind Nginx</span>
      </footer>
    </div>
  );
}
