"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  UserDocument,
  getDocuments,
  uploadDocuments,
  deleteDocument,
  getDocumentPreview,
  DocumentPreview,
} from "@/lib/api";

interface DocumentUploaderProps {
  selectedDocIds: string[];
  onSelectedDocsChange: (ids: string[]) => void;
  onPreviewDoc?: (preview: DocumentPreview) => void;
}

export default function DocumentUploader({
  selectedDocIds,
  onSelectedDocsChange,
  onPreviewDoc,
}: DocumentUploaderProps) {
  const [documents, setDocuments] = useState<UserDocument[]>([]);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadProgressStage, setUploadProgressStage] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load existing uploaded documents on mount
  useEffect(() => {
    loadDocs();
  }, []);

  const loadDocs = async () => {
    try {
      const docs = await getDocuments();
      setDocuments(docs);
      // Auto-select all ready documents initially if none selected
      if (selectedDocIds.length === 0 && docs.length > 0) {
        onSelectedDocsChange(docs.filter((d) => d.status === "ready").map((d) => d.document_id));
      }
    } catch (err: any) {
      console.error("Failed to load documents:", err);
    }
  };

  const handleFiles = async (files: FileList | File[]) => {
    const validFiles: File[] = [];
    const rejected: string[] = [];
    const supportedExtensions = [".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".xlsx", ".xls"];

    Array.from(files).forEach((file) => {
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      if (supportedExtensions.includes(ext)) {
        validFiles.push(file);
      } else {
        rejected.push(file.name);
      }
    });

    if (rejected.length > 0) {
      setError(`Unsupported file(s): ${rejected.join(", ")}. Supported formats: PDF, Word (docx/doc), Text (txt/md), CSV, Excel (xlsx/xls).`);
    } else {
      setError(null);
    }

    if (validFiles.length === 0) return;

    setUploading(true);
    setUploadProgressStage("Uploading files...");

    try {
      // Staged feedback
      setTimeout(() => setUploadProgressStage("Extracting text and tables..."), 600);
      setTimeout(() => setUploadProgressStage("Generating chunks and ONNX embeddings..."), 1200);

      const uploaded = await uploadDocuments(validFiles);
      setDocuments((prev) => [...uploaded, ...prev.filter((p) => !uploaded.some((u) => u.document_id === p.document_id))]);

      // Automatically select newly uploaded ready documents
      const newReadyIds = uploaded.filter((d) => d.status === "ready").map((d) => d.document_id);
      onSelectedDocsChange([...Array.from(new Set([...selectedDocIds, ...newReadyIds]))]);
      setUploadProgressStage("Ready!");
      setTimeout(() => setUploadProgressStage(""), 1500);
    } catch (err: any) {
      setError(err?.message || "Failed to process and index document.");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.document_id !== docId));
      onSelectedDocsChange(selectedDocIds.filter((id) => id !== docId));
    } catch (err: any) {
      setError("Failed to delete document.");
    }
  };

  const handlePreview = async (docId: string) => {
    if (!onPreviewDoc) return;
    try {
      const preview = await getDocumentPreview(docId);
      onPreviewDoc(preview);
    } catch (err) {
      console.error("Preview error:", err);
    }
  };

  const toggleSelect = (docId: string) => {
    if (selectedDocIds.includes(docId)) {
      onSelectedDocsChange(selectedDocIds.filter((id) => id !== docId));
    } else {
      onSelectedDocsChange([...selectedDocIds, docId]);
    }
  };

  const selectAll = () => {
    const readyIds = documents.filter((d) => d.status === "ready").map((d) => d.document_id);
    if (selectedDocIds.length === readyIds.length) {
      onSelectedDocsChange([]);
    } else {
      onSelectedDocsChange(readyIds);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1048576).toFixed(1) + " MB";
  };

  const getBadgeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case "pdf":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";
      case "docx":
      case "doc":
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
      case "xlsx":
      case "xls":
      case "csv":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      default:
        return "bg-zinc-800 text-zinc-300 border-zinc-700";
    }
  };

  return (
    <div className="w-full space-y-3">
      {/* ── Drop Zone ─────────────────────────────────────────── */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragOver(false);
          if (e.dataTransfer.files) handleFiles(e.dataTransfer.files);
        }}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-2xl p-4 text-center cursor-pointer transition-all ${
          isDragOver
            ? "border-blue-500 bg-blue-950/20"
            : "border-zinc-800 bg-[#0e0e12]/60 hover:border-zinc-700 hover:bg-[#121217]"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.doc,.txt,.md,.csv,.xlsx,.xls"
          className="hidden"
          onChange={(e) => {
            if (e.target.files) handleFiles(e.target.files);
            e.target.value = "";
          }}
        />

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-zinc-800/80 border border-zinc-700/60 flex items-center justify-center text-zinc-300">
            {uploading ? (
              <svg className="w-5 h-5 animate-spin text-blue-400" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            )}
          </div>
          <div className="text-left">
            <p className="text-xs font-semibold text-white">
              {uploading ? uploadProgressStage || "Processing document..." : "Upload documents for RAG & Analysis"}
            </p>
            <p className="text-[11px] text-zinc-400">
              Drag & drop or browse · PDF, Word, Excel, CSV, Text (max 25MB)
            </p>
          </div>
        </div>
      </div>

      {/* ── Error Callout ─────────────────────────────────────── */}
      {error && (
        <div className="p-2.5 rounded-xl bg-red-950/40 border border-red-800/60 text-red-300 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-white text-xs ml-2 font-bold">
            ✕
          </button>
        </div>
      )}

      {/* ── Document List ─────────────────────────────────────── */}
      {documents.length > 0 && (
        <div className="space-y-2 bg-[#0c0c10] border border-zinc-800/80 rounded-2xl p-3">
          <div className="flex items-center justify-between text-xs text-zinc-400 px-1 pb-1 border-b border-zinc-800/60">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={selectedDocIds.length > 0 && selectedDocIds.length === documents.filter((d) => d.status === "ready").length}
                onChange={selectAll}
                className="rounded bg-zinc-900 border-zinc-700 text-blue-500 focus:ring-0 cursor-pointer"
              />
              <span className="font-semibold text-zinc-300">
                Uploaded Knowledge ({documents.length})
              </span>
            </div>
            <span className="text-[11px] text-zinc-500">
              {selectedDocIds.length} of {documents.filter((d) => d.status === "ready").length} active for queries
            </span>
          </div>

          <div className="max-h-48 overflow-y-auto divide-y divide-zinc-800/40 pr-1">
            {documents.map((doc) => {
              const isSelected = selectedDocIds.includes(doc.document_id);
              const isReady = doc.status === "ready";

              return (
                <div
                  key={doc.document_id}
                  onClick={() => isReady && toggleSelect(doc.document_id)}
                  className={`flex items-center justify-between py-2 px-1.5 rounded-lg text-xs transition cursor-pointer ${
                    isSelected ? "bg-zinc-800/40" : "hover:bg-zinc-800/20"
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      disabled={!isReady}
                      onChange={() => toggleSelect(doc.document_id)}
                      onClick={(e) => e.stopPropagation()}
                      className="rounded bg-zinc-900 border-zinc-700 text-blue-500 focus:ring-0 disabled:opacity-40 cursor-pointer"
                    />
                    <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border ${getBadgeColor(doc.file_type)}`}>
                      {doc.file_type}
                    </span>
                    <span
                      onClick={(e) => {
                        e.stopPropagation();
                        handlePreview(doc.document_id);
                      }}
                      className="truncate max-w-[220px] sm:max-w-xs text-zinc-200 font-medium hover:text-blue-400 hover:underline"
                      title={doc.filename}
                    >
                      {doc.filename}
                    </span>
                    <span className="text-[10px] text-zinc-500 hidden sm:inline">
                      {formatBytes(doc.file_size)}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {/* Status Pill */}
                    {isReady ? (
                      <span className="text-[10px] text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-2 py-0.5 rounded-full font-mono flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                        {doc.chunk_count} chunks
                      </span>
                    ) : doc.status === "processing" ? (
                      <span className="text-[10px] text-amber-400 bg-amber-950/40 border border-amber-800/40 px-2 py-0.5 rounded-full font-mono flex items-center gap-1">
                        <svg className="w-2.5 h-2.5 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                        </svg>
                        {doc.stage || "processing"}
                      </span>
                    ) : (
                      <span
                        className="text-[10px] text-red-400 bg-red-950/40 border border-red-800/40 px-2 py-0.5 rounded-full font-mono"
                        title={doc.error_message || "Processing failed"}
                      >
                        failed
                      </span>
                    )}

                    {/* Preview Button */}
                    {isReady && onPreviewDoc && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handlePreview(doc.document_id);
                        }}
                        className="text-zinc-400 hover:text-white text-[11px] p-1 rounded hover:bg-zinc-800"
                        title="Preview document"
                      >
                        👁
                      </button>
                    )}

                    {/* Delete Button */}
                    <button
                      onClick={(e) => handleDelete(doc.document_id, e)}
                      className="text-zinc-500 hover:text-red-400 text-xs p-1 rounded hover:bg-zinc-800 transition"
                      title="Remove document and unindex"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
