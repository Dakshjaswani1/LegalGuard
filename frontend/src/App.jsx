import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE = "http://127.0.0.1:8000/api/contracts/";

function App() {
  // --- DATA STATES ---
  const [contracts, setContracts] = useState([]);  // ✅ Fixed: Initialize as empty array
  const [result, setResult] = useState(null);      // ✅ Fixed: Added [result, setResult]
  const [loading, setLoading] = useState(false);

  // --- FORM STATES ---
  const [title, setTitle] = useState("");          // ✅ Fixed: Added [title, setTitle]
  const [file, setFile] = useState(null);
  const [error, setError] = useState(null);        // ✅ Added: Error state
  const [uploading, setUploading] = useState(false); // ✅ Added: Upload loading state

  // --- FETCH CONTRACTS ON MOUNT ---
  useEffect(() => {
    fetchList();
  }, []); // ✅ Fixed: Changed }, ) to }, []

  // --- FETCH CONTRACTS FROM API ---
  const fetchList = async () => {
    try {
      setError(null);
      const res = await axios.get(API_BASE);
      setContracts(res.data || []); // ✅ Fixed: Changed || ) to || []
    } catch (err) {
      const errorMsg = "Failed to fetch contracts. Is Django running?";
      setError(errorMsg);
      console.error(errorMsg, err);
      setContracts([]);
    }
  };

  // --- UPLOAD FILE ---
  const uploadFile = async (e) => {
    e.preventDefault();

    // ✅ Added: Validation
    if (!title.trim() || !file) {
      setError("Please enter title and select a file");
      return;
    }

    // ✅ Added: File validation
    const MAX_SIZE = 10 * 1024 * 1024; // 10MB
    if (file.size > MAX_SIZE) {
      setError("File size must be less than 10MB");
      return;
    }

    const ALLOWED_TYPES = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    if (!ALLOWED_TYPES.includes(file.type)) {
      setError("Only PDF and Word documents are allowed");
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("title", title);
      formData.append("file", file); // ✅ Fixed: file is now a File object
      
      await axios.post(API_BASE, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      
      setTitle("");     // ✅ Fixed: setTitle was undefined
      setFile(null);    // ✅ Added: Reset file input
      setError(null);
      fetchList();
    } catch (err) {
      const errorMsg = err.response?.data?.message || "Upload failed";
      setError(errorMsg);
      console.error("Upload error:", err);
    } finally {
      setUploading(false);
    }
  };

  // --- RUN AI AUDIT ---
  const runAudit = async (id) => {
    if (loading) return; // ✅ Added: Prevent multiple requests

    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${API_BASE}${id}/audit/`);
      setResult(res.data.audit_results);
      fetchList();
    } catch (err) {
      const errorMsg = "AI audit failed. Check console.";
      setError(errorMsg);
      console.error("Audit error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '30px', maxWidth: '900px', margin: 'auto', fontFamily: 'sans-serif' }}>
      <h1>LegalGuard MVP v0</h1>

      {/* ✅ Added: Error display */}
      {error && (
        <div style={{
          background: '#ffebee',
          border: '1px solid #c62828',
          color: '#b71c1c',
          padding: '12px',
          borderRadius: '4px',
          marginBottom: '20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* 1. UPLOAD FORM */}
      <div style={{ border: '1px solid #ddd', padding: '20px', marginBottom: '20px', borderRadius: '4px' }}>
        <h3>1. Add Legal Document</h3>
        <form onSubmit={uploadFile}>
          <div style={{ marginBottom: '10px' }}>
            <input
              type="text"
              placeholder="Document Title"
              value={title}
              onChange={e => setTitle(e.target.value)}
              disabled={uploading}
              style={{ width: '100%', padding: '8px', marginBottom: '10px', boxSizing: 'border-box' }}
            />
          </div>

          <div style={{ marginBottom: '10px' }}>
            <input
              type="file"
              accept=".pdf,.doc,.docx"
              onChange={e => setFile(e.target.files?.[0])} // ✅ Fixed: Get first file, not FileList
              disabled={uploading}
              style={{ width: '100%', marginBottom: '10px' }}
            />
            {file && (
              <p style={{ fontSize: '12px', color: '#666' }}>
                Selected: <strong>{file.name}</strong> ({(file.size / 1024).toFixed(2)} KB)
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={uploading || !title.trim() || !file}
            style={{
              background: uploading ? '#ccc' : '#007bff',
              color: 'white',
              border: 'none',
              padding: '10px 20px',
              borderRadius: '4px',
              cursor: uploading ? 'not-allowed' : 'pointer',
              fontSize: '14px'
            }}
          >
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </form>
      </div>

      {/* 2. CONTRACT LIST */}
      <div style={{ marginBottom: '20px' }}>
        <h3>2. Uploaded Documents ({contracts?.length || 0})</h3>
        {!contracts || contracts.length === 0 ? (
          <p style={{ color: '#999' }}>No documents uploaded yet.</p>
        ) : (
          <div>
            {contracts.map(c => ( // ✅ Fixed: Added optional chaining
              <div
                key={c.id}
                style={{
                  padding: '12px',
                  borderBottom: '1px solid #eee',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div>
                  <p style={{ margin: '0 0 5px 0', fontWeight: 'bold' }}>{c.title}</p>
                  <p style={{ margin: '0', fontSize: '12px', color: '#666' }}>Status: {c.status}</p>
                </div>
                <button
                  onClick={() => runAudit(c.id)}
                  disabled={loading}
                  style={{
                    background: loading ? '#ccc' : '#28a745',
                    color: 'white',
                    border: 'none',
                    padding: '8px 16px',
                    borderRadius: '4px',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    fontSize: '12px',
                    whiteSpace: 'nowrap'
                  }}
                >
                  {loading ? "Auditing..." : "Audit"} {/* ✅ Fixed: Typo "Auditng" -> "Auditing" */}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 3. AI AUDIT RESULTS */}
      <div style={{ background: '#f9f9f9', padding: '20px', borderRadius: '4px' }}>
        <h3>3. AI Audit Results</h3>
        {!result ? (
          <p style={{ color: '#999' }}>No audit results yet. Select a document and click "Audit".</p>
        ) : (
          <div>
            <p style={{ marginBottom: '15px' }}>
              <strong>Summary:</strong> {result.summary}
            </p>
            
            {/* ✅ Added: Compliance status */}
            <p style={{
              padding: '10px',
              background: result.is_compliant ? '#d4edda' : '#f8d7da',
              color: result.is_compliant ? '#155724' : '#721c24',
              borderRadius: '4px',
              marginBottom: '15px'
            }}>
              <strong>Safe to Sign:</strong> {result.is_compliant ? '✅ YES' : '❌ NO'}
            </p>

            <h4>Findings:</h4>
            {result.findings && result.findings.length > 0 ? (
              result.findings.map((f, i) => (
                <div
                  key={i}
                  style={{
                    borderLeft: f.risk_level === 'High' ? '4px solid #dc3545' : '4px solid #ffc107',
                    paddingLeft: '10px',
                    margin: '10px 0',
                    padding: '10px 0 10px 10px',
                    background: f.risk_level === 'High' ? '#fff5f5' : '#fffbf0',
                    borderRadius: '4px'
                  }}
                >
                  <p style={{ margin: '0 0 5px 0' }}>
                    <strong>{f.clause_name}</strong> 
                    <span style={{
                      background: f.risk_level === 'High' ? '#dc3545' : '#ffc107',
                      color: f.risk_level === 'High' ? 'white' : 'black',
                      padding: '2px 8px',
                      borderRadius: '3px',
                      marginLeft: '10px',
                      fontSize: '12px'
                    }}>
                      {f.risk_level} Risk
                    </span>
                  </p>
                  <p style={{ margin: '5px 0', color: '#333' }}>{f.explanation}</p>
                  {f.suggestion && (
                    <p style={{ margin: '5px 0', color: '#0056b3', fontStyle: 'italic' }}>
                      💡 <strong>Suggestion:</strong> {f.suggestion}
                    </p>
                  )}
                </div>
              ))
            ) : (
              <p style={{ color: '#999' }}>No findings detected.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
