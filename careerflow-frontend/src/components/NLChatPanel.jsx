import React, { useState } from "react";

/**
 * Try to turn the backend 'result' object into something we can show nicely.
 * Handles both:
 * - natural language reply (just text)
 * - JSON-style reply (with summary, match_score, gaps, suggestions, etc.)
 */
function buildChatView(result) {
  if (!result) return null;

  let reply = result.reply;
  let structured = result.structured || {};
  let chat = {
    summary: null,
    matchScore: null,
    gaps: [],
    suggestions: [],
    bulletPoints: [],
    text: null,
  };

  // 1) If reply is a string, see if it's JSON
  if (typeof reply === "string") {
    const trimmed = reply.trim();
    let parsed = null;

    if (
      (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
      (trimmed.startsWith("[") && trimmed.endsWith("]"))
    ) {
      try {
        parsed = JSON.parse(trimmed);
      } catch {
        // ignore JSON parse error; we'll just treat as plain text below
      }
    }

    if (parsed) {
      // Often the model returns { "response": {...} }
      const resp = parsed.response || parsed;

      chat.summary = resp.summary || null;
      if (typeof resp.match_score === "number") {
        chat.matchScore = resp.match_score;
      }
      if (Array.isArray(resp.gaps)) chat.gaps = resp.gaps;
      if (Array.isArray(resp.suggestions)) chat.suggestions = resp.suggestions;
      if (Array.isArray(resp.bullet_points))
        chat.bulletPoints = resp.bullet_points;
    } else {
      // Plain text reply (this is what translations will usually be)
      chat.text = reply;
    }
  }

  // 2) If reply was already an object
  if (!chat.summary && reply && typeof reply === "object") {
    const resp = reply.response || reply;
    chat.summary = resp.summary || null;
    if (typeof resp.match_score === "number") {
      chat.matchScore = resp.match_score;
    }
    if (Array.isArray(resp.gaps)) chat.gaps = resp.gaps;
    if (Array.isArray(resp.suggestions)) chat.suggestions = resp.suggestions;
    if (Array.isArray(resp.bullet_points))
      chat.bulletPoints = resp.bullet_points;
  }

  // 3) Fallback to the structured job_match data if reply didn't include it
  const jm = structured.job_match;
  if (jm) {
    if (chat.matchScore == null && typeof jm.match_score === "number") {
      chat.matchScore = jm.match_score;
    }
    if (!chat.gaps?.length && Array.isArray(jm.gaps)) {
      chat.gaps = jm.gaps;
    }
    if (!chat.suggestions?.length && Array.isArray(jm.suggestions)) {
      chat.suggestions = jm.suggestions;
    }
  }

  // 4) Fallback bullets from section_enhance
  const se = structured.section_enhance;
  if (!chat.bulletPoints?.length && se) {
    if (Array.isArray(se.bullet_points)) {
      chat.bulletPoints = se.bullet_points;
    } else if (Array.isArray(se.edits)) {
      // turn edits into "After: ..." bullet suggestions
      chat.bulletPoints = se.edits.map((e) => e.after || e.before);
    }
  }

  // If everything is empty and we have no text, fall back to JSON string
  if (
    !chat.text &&
    !chat.summary &&
    chat.matchScore == null &&
    !chat.gaps.length &&
    !chat.suggestions.length &&
    !chat.bulletPoints.length &&
    typeof reply === "string"
  ) {
    chat.text = reply;
  }

  return chat;
}

/**
 * Build a single text blob that we can send to /export_pdf_from_text
 * so the backend can render a clean, structured PDF.
 */
function buildExportText(chatView, rawResult) {
  if (!chatView) return "";

  // If it's a translation or long free-text reply, just export that.
  if (chatView.text && chatView.text.trim()) {
    return chatView.text.trim();
  }

  const lines = [];

  if (chatView.summary) {
    lines.push(chatView.summary.trim(), "");
  }

  if (chatView.matchScore != null) {
    const pct =
      chatView.matchScore <= 1
        ? Math.round(chatView.matchScore * 100)
        : Math.round(chatView.matchScore);
    lines.push(`Job Match Score: ${pct}%`, "");
  }

  if (chatView.gaps?.length) {
    lines.push("Skill Gaps:");
    chatView.gaps.forEach((g) => lines.push(`• ${g}`));
    lines.push("");
  }

  if (chatView.suggestions?.length) {
    lines.push("Suggestions to Improve Match:");
    chatView.suggestions.forEach((s) => lines.push(`• ${s}`));
    lines.push("");
  }

  if (chatView.bulletPoints?.length) {
    lines.push("Suggested Bullet Improvements:");
    chatView.bulletPoints.forEach((b) => lines.push(`• ${b}`));
    lines.push("");
  }

  // Fallback: raw JSON as text
  if (!lines.length && rawResult) {
    lines.push(JSON.stringify(rawResult, null, 2));
  }

  return lines.join("\n");
}

export default function NLChatPanel({ apiBase, resumeVersionId }) {
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [chatView, setChatView] = useState(null);
  const [rawResult, setRawResult] = useState(null);

  const handleAsk = async () => {
    setError("");
    setChatView(null);

    if (!resumeVersionId) {
      setError("Please select or upload a resume version first.");
      return;
    }
    if (!message.trim()) {
      setError("Please type what you want help with.");
      return;
    }

    setIsLoading(true);
    try {
      const res = await fetch(`${apiBase}/chat_nl`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          resume_version_id: resumeVersionId,
          user_message: message,
          conversation_id: "default-conversation",
        }),
      });

      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`Backend error (${res.status}): ${txt}`);
      }

      const data = await res.json();
      const result = data.result || {};
      setRawResult(result);

      const parsedView = buildChatView(result);
      setChatView(parsedView);
    } catch (err) {
      console.error("Failed to call /chat_nl:", err);
      setError("Failed to call /chat_nl. Check the backend logs for details.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!chatView && !rawResult) {
      alert("No content to export yet. Ask the agent first.");
      return;
    }

    const textToExport = buildExportText(chatView, rawResult).trim();
    if (!textToExport) {
      alert("Nothing exportable was found in the agent reply.");
      return;
    }

    try {
      const res = await fetch(`${apiBase}/export_pdf_from_text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: textToExport,
          file_name: "resume_chat_export.pdf",
        }),
      });

      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || "Failed to export PDF");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "resume_chat_export.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download PDF from chat output:", err);
      alert("Failed to download PDF from chat output.");
    }
  };

  return (
    <div className="mt-8 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 className="text-xl font-semibold mb-2">
        Natural Language Chat (Agents)
      </h2>
      <p className="text-sm text-gray-600 mb-4">
        Describe what you want, and the system will decide which agents to run
        (job match, bullet enhancer, company research, translation, etc.).
      </p>

      <textarea
        className="w-full border border-gray-300 rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        rows={6}
        placeholder={`Examples:
- Optimize my resume for Google using this job description...
- Make my bullets more data-driven for an AI Engineer role.
- Translate my resume to Japanese for the Japan market.`}
        value={message}
        onChange={(e) => setMessage(e.target.value)}
      />

      {error && <div className="mt-2 text-sm text-red-600">{error}</div>}

      <div className="mt-3 flex items-center gap-3">
        <button
          onClick={handleAsk}
          disabled={isLoading}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md shadow-sm hover:bg-blue-700 disabled:opacity-60"
        >
          {isLoading ? "Asking..." : "Ask Agent"}
        </button>

        {chatView && (
          <button
            onClick={handleDownloadPdf}
            className="inline-flex items-center px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md shadow-sm hover:bg-green-700"
          >
            Download as PDF
          </button>
        )}

        {isLoading && (
          <span className="text-xs text-gray-500">
            Running agents on your request…
          </span>
        )}
      </div>

      {/* Chat-style Answer */}
      <div className="mt-6">
        <h3 className="text-lg font-semibold mb-2">Agent Reply</h3>

        {!chatView && !rawResult && !error && (
          <p className="text-sm text-gray-500">
            Ask something above to see the agent&apos;s reply.
          </p>
        )}

        {chatView && (
          <div className="space-y-4 text-sm">
            {chatView.summary && (
              <div className="font-semibold text-gray-900">
                {chatView.summary}
              </div>
            )}

            {chatView.text && (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 whitespace-pre-line">
                {chatView.text}
              </div>
            )}

            {chatView.matchScore != null && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-baseline justify-between">
                <div>
                  <div className="uppercase text-xs tracking-wide text-gray-500">
                    Job Match Score
                  </div>
                  <div className="text-xs text-gray-600">
                    How well your resume aligns with this request/JD.
                  </div>
                </div>
                <div className="text-3xl font-bold text-green-600">
                  {Math.round(
                    (chatView.matchScore <= 1
                      ? chatView.matchScore * 100
                      : chatView.matchScore
                    )
                  )}
                  %
                </div>
              </div>
            )}

            {chatView.gaps?.length > 0 && (
              <div>
                <div className="font-semibold mb-1">Skill Gaps</div>
                <ul className="list-disc list-inside space-y-1 text-gray-700">
                  {chatView.gaps.map((g, idx) => (
                    <li key={idx}>{g}</li>
                  ))}
                </ul>
              </div>
            )}

            {chatView.suggestions?.length > 0 && (
              <div>
                <div className="font-semibold mb-1">
                  Suggestions to Improve Match
                </div>
                <ul className="list-disc list-inside space-y-1 text-gray-700">
                  {chatView.suggestions.map((s, idx) => (
                    <li key={idx}>{s}</li>
                  ))}
                </ul>
              </div>
            )}

            {chatView.bulletPoints?.length > 0 && (
              <div>
                <div className="font-semibold mb-1">
                  Suggested Bullet Improvements
                </div>
                <ol className="list-decimal list-inside space-y-1 text-gray-700">
                  {chatView.bulletPoints.map((b, idx) => (
                    <li key={idx}>{b}</li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        )}

        {/* Raw JSON debug */}
        {rawResult && (
          <div className="mt-6">
            <details className="text-xs">
              <summary className="cursor-pointer font-medium text-gray-700">
                Raw JSON (debug)
              </summary>
              <pre className="mt-2 bg-gray-900 text-gray-100 p-3 rounded-md overflow-x-auto text-[11px] leading-tight">
                {JSON.stringify(rawResult, null, 2)}
              </pre>
            </details>
          </div>
        )}
      </div>
    </div>
  );
}
