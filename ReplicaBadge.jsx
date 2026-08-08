import React from "react";

/**
 * The page's signature element: a small tag showing which backend replica
 * (backend_1 / backend_2) actually processed a given message. This is the
 * whole point of the demo made visible — proof that messages are being
 * served by different instances yet staying perfectly in sync via Redis.
 */
export default function ReplicaBadge({ instanceId }) {
  if (!instanceId) return null;
  const short = instanceId.replace("backend_", "R");
  return (
    <span className="replica-badge mono" title={`Served by ${instanceId}`}>
      <span className="replica-dot" />
      {short}
    </span>
  );
}
