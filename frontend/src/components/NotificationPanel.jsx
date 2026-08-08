import React from "react";

export default function NotificationPanel({ notifications, onRefresh }) {
  return (
    <div className="panel notif-panel">
      <div className="panel-head">
        <span className="tag-title">Async notification queue</span>
        <button className="ghost-btn small" onClick={onRefresh}>Refresh</button>
      </div>
      {notifications.length === 0 && (
        <div className="empty-state">No notifications yet — send one from the form above.</div>
      )}
      <ul className="notif-list">
        {notifications.map((n) => (
          <li key={n.id} className="notif-row">
            <span className={`status-dot ${n.delivered ? "status-ok" : "status-pending"}`} />
            <div className="notif-body">
              <div className="notif-title">{n.title}</div>
              <div className="notif-meta mono">
                to {n.recipient} · {n.delivered ? "delivered" : "queued — worker will pick it up"}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
