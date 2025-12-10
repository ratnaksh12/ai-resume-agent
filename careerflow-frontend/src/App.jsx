import React, { useState, useCallback, useEffect } from "react";
import UploadResume from "./components/UploadResume";
import VersionsPanel from "./components/VersionsPanel";
import ChatPanel from "./components/ChatPanel";
import NLChatPanel from "./components/NLChatPanel";

const API_BASE = "http://127.0.0.1:8000";

export default function App() {
  const [resumeId, setResumeId] = useState(null);
  const [versions, setVersions] = useState([]);
  const [selectedVersionId, setSelectedVersionId] = useState(null);

  const fetchVersions = useCallback(async () => {
    if (!resumeId) return;
    try {
      const res = await fetch(`${API_BASE}/resume/${resumeId}/versions`);
      const data = await res.json();
      setVersions(data.versions || []);

      if (data.versions && data.versions.length > 0) {
        // assume newest first
        setSelectedVersionId(data.versions[0].version_id);
      }
    } catch (err) {
      console.error("Failed to fetch versions:", err);
    }
  }, [resumeId]);

  // when resumeId changes, load its versions
  useEffect(() => {
    fetchVersions();
  }, [fetchVersions]);

  const handleUploaded = (newResumeId, versionId) => {
    setResumeId(newResumeId);
    setSelectedVersionId(versionId);
    // refresh full list
    fetchVersions();
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* LEFT SIDE: Upload + Versions */}
        <div className="space-y-6">
          <UploadResume apiBase={API_BASE} onUploaded={handleUploaded} />

          <VersionsPanel
            versions={versions}
            selectedVersionId={selectedVersionId}
            onSelectVersion={setSelectedVersionId}
          />
        </div>

        {/* RIGHT SIDE: Chat / Optimize */}
        <div className="md:col-span-2 space-y-6">
          {/* Original structured chat (job_match, section_enhance, etc.) */}
          <ChatPanel
            apiBase={API_BASE}
            resumeId={resumeId}
            resumeVersionId={selectedVersionId}
            onUpdateVersions={fetchVersions}
          />

          {/* New natural-language chat that hits /chat_nl */}
          <NLChatPanel
            apiBase={API_BASE}
            resumeVersionId={selectedVersionId}
          />
        </div>
      </div>
    </div>
  );
}
