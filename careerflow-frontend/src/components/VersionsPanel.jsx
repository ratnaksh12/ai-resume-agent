import React from "react";

export default function VersionsPanel({
  versions,
  selectedVersionId,
  onSelectVersion,
}) {
  return (
    <div className="bg-white p-6 rounded-xl shadow">
      <h2 className="font-semibold text-xl mb-4">Resume Versions</h2>

      {!versions || versions.length === 0 ? (
        <div className="text-sm text-gray-500">
          Upload a resume to see versions.
        </div>
      ) : (
        <div className="space-y-3 max-h-72 overflow-y-auto text-sm">
          {versions.map((v) => (
            <button
              key={v.version_id}
              onClick={() => onSelectVersion && onSelectVersion(v.version_id)}
              className={`w-full text-left p-3 rounded border ${
                v.version_id === selectedVersionId
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 bg-gray-50 hover:bg-gray-100"
              }`}
            >
              <div className="font-semibold">
                Version {v.version_id}
              </div>
              <div className="text-xs text-gray-500">
                Created: {v.created_at}
              </div>
              <div className="mt-1 text-xs text-gray-600 line-clamp-3">
                {v.metadata_preview}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
