import React, { useState } from "react";

function safeParseJSON(value) {
  if (!value) return null;
  if (typeof value === "object") return value;
  try {
    return JSON.parse(value);
  } catch (e) {
    console.warn("Failed to parse JSON from LLM:", e);
    return null;
  }
}

export default function ChatPanel({
  apiBase,
  resumeVersionId,
  resumeId,
  onUpdateVersions,
}) {
  const [jobDesc, setJobDesc] = useState("");
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("Software Engineer");

  const [loading, setLoading] = useState(false);
  const [rawResult, setRawResult] = useState(null);

  const [jobMatch, setJobMatch] = useState(null);
  const [sectionEnhance, setSectionEnhance] = useState(null);
  const [companyResearch, setCompanyResearch] = useState(null);

  const runAgents = async () => {
    if (!jobDesc.trim()) {
      alert("Please paste a Job Description first.");
      return;
    }

    setLoading(true);
    setRawResult(null);
    setJobMatch(null);
    setSectionEnhance(null);
    setCompanyResearch(null);

    const payload = {
      resume_version_id: resumeVersionId || null,
      user_message:
        "Analyze how well my resume matches this job description, suggest improved bullet points, and give me company research if a company is provided.",
      job_description: jobDesc,
      company_name: company || "",
      role: role || "Software Engineer",
    };

    try {
      const res = await fetch(`${apiBase}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      const result = data.result || {};
      setRawResult(result);

      const jm = safeParseJSON(result.job_match);
      if (jm) setJobMatch(jm);

      const se = safeParseJSON(result.section_enhance);
      if (se) setSectionEnhance(se);

      const cr = safeParseJSON(result.company_research);
      if (cr) setCompanyResearch(cr);
    } catch (err) {
      console.error(err);
      alert("Something went wrong while calling the backend.");
    } finally {
      setLoading(false);
    }
  };

  const applyEdits = async (edits) => {
    if (!edits || edits.length === 0) {
      alert("No edits to apply.");
      return;
    }
    if (!resumeId) {
      alert("Upload a resume first so edits can be saved as a new version.");
      return;
    }

    try {
      let baseVersionId = resumeVersionId || null;
      try {
        const r = await fetch(`${apiBase}/resume/${resumeId}/versions`);
        const jr = await r.json();
        if (jr.versions && jr.versions.length > 0) {
          baseVersionId = jr.versions[0].version_id;
        }
      } catch (e) {
        console.warn("Could not fetch latest versions, falling back:", e);
      }

      if (!baseVersionId) {
        alert("Could not determine a base resume version to apply edits.");
        return;
      }

      const payload = {
        resume_id: resumeId,
        base_version_id: baseVersionId,
        edits,
      };

      const res = await fetch(`${apiBase}/apply_changes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      alert(`Edits applied. New version id: ${data.new_version_id}`);

      if (onUpdateVersions) onUpdateVersions();
    } catch (err) {
      console.error(err);
      alert("Failed to apply edits to resume.");
    }
  };

  const scoreDisplay = (() => {
    if (!jobMatch || jobMatch.score == null) return null;
    let s = jobMatch.score;
    if (s <= 1) s = Math.round(s * 100);
    else s = Math.round(s);
    return `${s}%`;
  })();

  return (
    <div className="bg-white p-6 rounded-xl shadow max-h-[90vh] overflow-y-auto">
      <h2 className="font-semibold text-xl mb-4">Chat / Optimize Resume</h2>

      {!resumeVersionId && (
        <div className="mb-3 text-xs text-yellow-700 bg-yellow-50 border border-yellow-200 rounded px-2 py-1">
          Tip: Upload a resume first for best Job Match results (otherwise the
          system has no resume text to analyze).
        </div>
      )}

      {/* Inputs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium mb-1">Role</label>
          <input
            className="border rounded w-full px-3 py-2 text-sm"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            placeholder="e.g. Backend Engineer"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Company</label>
          <input
            className="border rounded w-full px-3 py-2 text-sm"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="Optional – enables company research"
          />
        </div>
      </div>

      <div className="mt-3">
        <label className="block text-sm font-medium mb-1">
          Job Description
        </label>
        <textarea
          rows={8}
          className="border rounded w-full px-3 py-2 text-sm"
          value={jobDesc}
          onChange={(e) => setJobDesc(e.target.value)}
          placeholder="Paste the job description here..."
        />
      </div>

      <div className="mt-4 flex items-center gap-3">
        <button
          className="bg-green-600 text-white px-5 py-2 rounded-md text-sm font-medium disabled:opacity-60"
          onClick={runAgents}
          disabled={loading}
        >
          {loading ? "Running..." : "Run Agents"}
        </button>

        {loading && (
          <span className="text-xs text-gray-500">
            Analyzing resume, JD, and company…
          </span>
        )}
      </div>

      {/* Results */}
      <div className="mt-6 space-y-4">
        <div className="flex items-center justify-between">

      <h3 className="font-semibold text-lg">Results</h3>

  {resumeVersionId && (
    <a
      href={`${apiBase}/resume/${resumeVersionId}/export_pdf`}
      target="_blank"
      rel="noopener noreferrer"
      className="text-sm bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700"
    >
      Download Resume PDF
    </a>
  )}
</div>


        {/* Job Match Summary (Option A) */}
        {jobMatch ? (
          <div className="border rounded-lg p-4 bg-gray-50">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-gray-700">
                  Job Match Score
                </div>
                <div className="text-xs text-gray-500">
                  How well your resume aligns with this JD.
                </div>
              </div>
              {scoreDisplay && (
                <div className="text-3xl font-bold text-green-600">
                  {scoreDisplay}
                </div>
              )}
            </div>

            {Array.isArray(jobMatch.gaps) && jobMatch.gaps.length > 0 && (
              <div className="mt-4">
                <div className="text-sm font-semibold mb-1">Skill Gaps</div>
                <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                  {jobMatch.gaps.map((gap, idx) => (
                    <li key={idx}>{gap}</li>
                  ))}
                </ul>
              </div>
            )}

            {Array.isArray(jobMatch.suggestions) &&
              jobMatch.suggestions.length > 0 && (
                <div className="mt-4">
                  <div className="text-sm font-semibold mb-1">
                    Suggestions to Improve Match
                  </div>
                  <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                    {jobMatch.suggestions.map((s, idx) => (
                      <li key={idx}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}
          </div>
        ) : rawResult ? (
          <div className="text-xs text-gray-500">
            No structured job_match data was returned. See raw JSON below.
          </div>
        ) : (
          <div className="text-sm text-gray-500">No result yet.</div>
        )}

        {/* Suggested Bullet Improvements (Option B) */}
        {sectionEnhance?.edits?.length > 0 && (
          <div className="border rounded-lg p-4 bg-white">
            <div className="flex items-center justify-between mb-2">
              <div>
                <div className="text-sm font-semibold">
                  Suggested Bullet Improvements
                </div>
                <div className="text-xs text-gray-500">
                  These are candidate edits the system would apply to your
                  resume bullets.
                </div>
              </div>
              <button
                className="text-xs bg-blue-600 text-white px-3 py-1 rounded-md"
                onClick={() => applyEdits(sectionEnhance.edits)}
              >
                Apply Edits as New Version
              </button>
            </div>

            <div className="space-y-3 mt-2">
              {sectionEnhance.edits.map((edit, idx) => (
                <div
                  key={idx}
                  className="border border-gray-200 rounded-md p-3 text-xs bg-gray-50"
                >
                  <div className="font-semibold mb-1">Bullet {idx + 1}</div>
                  {edit.before && (
                    <div className="mb-1">
                      <span className="font-medium text-gray-500">
                        Before:
                      </span>{" "}
                      <span className="line-through text-gray-500">
                        {edit.before}
                      </span>
                    </div>
                  )}
                  {edit.after && (
                    <div className="mb-1">
                      <span className="font-medium text-gray-700">
                        After:
                      </span>{" "}
                      <span className="text-gray-900">{edit.after}</span>
                    </div>
                  )}
                  {edit.explanation && (
                    <div className="mt-1 text-gray-600">
                      <span className="font-medium">Why:</span>{" "}
                      {edit.explanation}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Company Research (Option C) */}
        {companyResearch && (
          <div className="border rounded-lg p-4 bg-gray-50">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-gray-700">
                  Company Research
                </div>
                <div className="text-xs text-gray-500">
                  Use this context when tailoring your bullets or cover letter.
                </div>
              </div>
              {companyResearch.company && (
                <div className="text-sm font-semibold text-blue-700">
                  {companyResearch.company}
                </div>
              )}
            </div>

            {companyResearch.about && (
              <p className="mt-3 text-sm text-gray-700">
                {companyResearch.about}
              </p>
            )}

            {companyResearch.tone && (
              <p className="mt-2 text-xs text-gray-500">
                Recommended tone for outreach and resume:{" "}
                <span className="font-medium text-gray-700">
                  {companyResearch.tone}
                </span>
              </p>
            )}

            {Array.isArray(companyResearch.keywords) &&
              companyResearch.keywords.length > 0 && (
                <div className="mt-3">
                  <div className="text-xs font-semibold text-gray-600 mb-1">
                    Keywords to weave into bullets or outreach:
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {companyResearch.keywords.map((kw, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center px-2 py-1 rounded-full text-[11px] bg-blue-50 text-blue-700 border border-blue-100"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}
          </div>
        )}

        {/* Raw JSON fallback (debug / transparency) */}
        {rawResult && (
          <div className="border rounded-lg p-3 bg-gray-900 text-gray-100 text-xs overflow-auto max-h-80">
            <div className="font-semibold mb-2 text-gray-200">
              Raw JSON (debug)
            </div>
            <pre>{JSON.stringify(rawResult, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  );
}
