"use client";

import CodeMirror from "@uiw/react-codemirror";
import { markdown } from "@codemirror/lang-markdown";
import {
  Download,
  FileText,
  LogOut,
  PanelRight,
  Plus,
  RotateCcw,
  Save,
  Search,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";

import {
  ApiError,
  api,
  type Backlink,
  type Note,
  type NoteLink,
  type NoteVersion,
  type SearchResult,
  type User,
} from "@/lib/api";

type AuthMode = "login" | "register";
type ViewMode = "edit" | "preview";
type ContextTab = "links" | "versions";

const tokenStorageKey = "mdvault.token";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("strong-password");
  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [draftBody, setDraftBody] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("edit");
  const [contextTab, setContextTab] = useState<ContextTab>("links");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [outgoingLinks, setOutgoingLinks] = useState<NoteLink[]>([]);
  const [backlinks, setBacklinks] = useState<Backlink[]>([]);
  const [versions, setVersions] = useState<NoteVersion[]>([]);
  const [isBusy, setIsBusy] = useState(false);
  const [message, setMessage] = useState("");

  const selectedNote = useMemo(
    () => notes.find((note) => note.id === selectedNoteId) ?? null,
    [notes, selectedNoteId],
  );

  const isDirty = selectedNote
    ? selectedNote.title !== draftTitle || selectedNote.body_markdown !== draftBody
    : false;

  const markdownExtensions = useMemo(() => [markdown()], []);

  const setSession = useCallback((nextToken: string, nextUser: User) => {
    localStorage.setItem(tokenStorageKey, nextToken);
    setToken(nextToken);
    setUser(nextUser);
  }, []);

  const clearSession = useCallback(() => {
    localStorage.removeItem(tokenStorageKey);
    setToken(null);
    setUser(null);
    setNotes([]);
    setSelectedNoteId(null);
    setSearchResults([]);
    setOutgoingLinks([]);
    setBacklinks([]);
    setVersions([]);
  }, []);

  const loadNotes = useCallback(
    async (activeToken: string, preferredNoteId?: string) => {
      const loadedNotes = await api.listNotes(activeToken);
      setNotes(loadedNotes);

      const nextSelectedId =
        preferredNoteId && loadedNotes.some((note) => note.id === preferredNoteId)
          ? preferredNoteId
          : loadedNotes[0]?.id ?? null;
      setSelectedNoteId(nextSelectedId);
    },
    [],
  );

  const refreshNoteContext = useCallback(
    async (noteId: string, activeToken = token) => {
      if (!activeToken) {
        return;
      }

      try {
        const [nextOutgoing, nextBacklinks, nextVersions] = await Promise.all([
          api.outgoingLinks(activeToken, noteId),
          api.backlinks(activeToken, noteId),
          api.versions(activeToken, noteId),
        ]);
        setOutgoingLinks(nextOutgoing);
        setBacklinks(nextBacklinks);
        setVersions(nextVersions);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          clearSession();
          return;
        }

        setMessage(error instanceof Error ? error.message : "Could not load note context");
      }
    },
    [clearSession, token],
  );

  useEffect(() => {
    const storedToken = localStorage.getItem(tokenStorageKey);
    if (!storedToken) {
      return;
    }

    api
      .me(storedToken)
      .then((currentUser) => {
        setSession(storedToken, currentUser);
        return loadNotes(storedToken);
      })
      .catch(() => {
        clearSession();
      });
  }, [clearSession, loadNotes, setSession]);

  useEffect(() => {
    if (!selectedNote) {
      setDraftTitle("");
      setDraftBody("");
      setOutgoingLinks([]);
      setBacklinks([]);
      setVersions([]);
      return;
    }

    setDraftTitle(selectedNote.title);
    setDraftBody(selectedNote.body_markdown);
    void refreshNoteContext(selectedNote.id);
  }, [refreshNoteContext, selectedNote]);

  async function runAction(action: () => Promise<void>) {
    setIsBusy(true);
    setMessage("");
    try {
      await action();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Something went wrong");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleAuth() {
    await runAction(async () => {
      if (authMode === "register") {
        await api.register(email, password);
      }
      const loginResponse = await api.login(email, password);
      const currentUser = await api.me(loginResponse.access_token);
      setSession(loginResponse.access_token, currentUser);
      await loadNotes(loginResponse.access_token);
    });
  }

  async function handleCreateNote() {
    if (!token) {
      return;
    }

    await runAction(async () => {
      const note = await api.createNote(token, "Untitled", "");
      await loadNotes(token, note.id);
      setViewMode("edit");
    });
  }

  async function handleSaveNote() {
    if (!token || !selectedNote) {
      return;
    }

    await runAction(async () => {
      const savedNote = await api.updateNote(token, selectedNote.id, {
        title: draftTitle,
        body_markdown: draftBody,
      });
      setNotes((currentNotes) =>
        currentNotes.map((note) => (note.id === savedNote.id ? savedNote : note)),
      );
      setSearchResults((currentResults) =>
        currentResults.map((result) =>
          result.note.id === savedNote.id ? { ...result, note: savedNote } : result,
        ),
      );
      await refreshNoteContext(savedNote.id, token);
      setMessage("Saved");
    });
  }

  async function handleDeleteNote() {
    if (!token || !selectedNote) {
      return;
    }

    await runAction(async () => {
      await api.deleteNote(token, selectedNote.id);
      await loadNotes(token);
      setMessage("Deleted");
    });
  }

  async function handleSearch(query: string) {
    setSearchQuery(query);
    if (!token || !query.trim()) {
      setSearchResults([]);
      return;
    }

    try {
      const results = await api.search(token, query);
      setSearchResults(results);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Search failed");
    }
  }

  async function handleRestoreVersion(versionId: string) {
    if (!token || !selectedNote) {
      return;
    }

    await runAction(async () => {
      const restoredNote = await api.restoreVersion(token, selectedNote.id, versionId);
      setNotes((currentNotes) =>
        currentNotes.map((note) => (note.id === restoredNote.id ? restoredNote : note)),
      );
      setSearchResults((currentResults) =>
        currentResults.map((result) =>
          result.note.id === restoredNote.id ? { ...result, note: restoredNote } : result,
        ),
      );
      setDraftTitle(restoredNote.title);
      setDraftBody(restoredNote.body_markdown);
      await refreshNoteContext(restoredNote.id, token);
      setMessage("Restored");
    });
  }

  async function handleExportNotes() {
    if (!token) {
      return;
    }

    await runAction(async () => {
      const zipBlob = await api.exportNotes(token);
      const objectUrl = URL.createObjectURL(zipBlob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = "mdvault-notes.zip";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(objectUrl);
      setMessage("Exported");
    });
  }

  if (!token || !user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#f5f7f2] px-4 py-8">
        <section className="w-full max-w-sm border border-line bg-white p-5 shadow-sm">
          <div className="mb-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">mdvault</p>
            <h1 className="mt-1 text-2xl font-semibold text-ink">Markdown workspace</h1>
          </div>

          <div className="mb-4 grid grid-cols-2 border border-line p-1">
            <button
              className={`px-3 py-2 text-sm font-medium ${authMode === "login" ? "bg-ink text-white" : "text-ink"}`}
              onClick={() => setAuthMode("login")}
              type="button"
            >
              Login
            </button>
            <button
              className={`px-3 py-2 text-sm font-medium ${authMode === "register" ? "bg-ink text-white" : "text-ink"}`}
              onClick={() => setAuthMode("register")}
              type="button"
            >
              Register
            </button>
          </div>

          <label className="mb-3 block text-sm font-medium text-ink">
            Email
            <input
              className="mt-1 w-full border border-line px-3 py-2 outline-none focus:border-moss"
              onChange={(event) => setEmail(event.target.value)}
              type="email"
              value={email}
            />
          </label>
          <label className="mb-4 block text-sm font-medium text-ink">
            Password
            <input
              className="mt-1 w-full border border-line px-3 py-2 outline-none focus:border-moss"
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              value={password}
            />
          </label>

          <button
            className="flex w-full items-center justify-center gap-2 bg-moss px-3 py-2 font-semibold text-white disabled:opacity-60"
            disabled={isBusy}
            onClick={handleAuth}
            type="button"
          >
            <FileText size={17} />
            {authMode === "login" ? "Login" : "Create account"}
          </button>

          {message ? <p className="mt-3 text-sm text-clay">{message}</p> : null}
        </section>
      </main>
    );
  }

  return (
    <main className="grid min-h-screen grid-cols-1 bg-[#f5f7f2] text-ink lg:grid-cols-[300px_minmax(0,1fr)_320px]">
      <aside className="border-b border-line bg-white lg:border-b-0 lg:border-r">
        <div className="flex h-16 items-center justify-between border-b border-line px-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">mdvault</p>
            <p className="max-w-[190px] truncate text-sm text-moss">{user.email}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              className="border border-line p-2 text-ink hover:border-moss hover:text-moss disabled:opacity-60"
              disabled={isBusy}
              onClick={handleExportNotes}
              title="Export notes"
              type="button"
            >
              <Download size={17} />
            </button>
            <button
              className="border border-line p-2 text-ink hover:border-clay hover:text-clay"
              onClick={clearSession}
              title="Log out"
              type="button"
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>

        <div className="border-b border-line p-3">
          <div className="flex items-center border border-line bg-[#f5f7f2] px-2">
            <Search size={16} className="text-moss" />
            <input
              className="w-full bg-transparent px-2 py-2 text-sm outline-none"
              onChange={(event) => handleSearch(event.target.value)}
              placeholder="Search notes"
              value={searchQuery}
            />
          </div>
        </div>

        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-moss">
            {searchQuery.trim() ? "Results" : "Notes"}
          </h2>
          <button
            className="flex items-center gap-1 bg-ink px-2 py-1 text-sm font-semibold text-white disabled:opacity-60"
            disabled={isBusy}
            onClick={handleCreateNote}
            type="button"
          >
            <Plus size={16} />
            New
          </button>
        </div>

        <nav className="max-h-[calc(100vh-184px)] overflow-auto">
          {(searchQuery.trim() ? searchResults.map((result) => result.note) : notes).map((note) => (
            <button
              className={`block w-full border-b border-line px-4 py-3 text-left hover:bg-[#eef2ea] ${
                selectedNoteId === note.id ? "bg-[#e7ede2]" : "bg-white"
              }`}
              key={note.id}
              onClick={() => setSelectedNoteId(note.id)}
              type="button"
            >
              <span className="block truncate text-sm font-semibold">{note.title}</span>
              <span className="mt-1 block text-xs text-moss">
                v{note.version_number} · {formatDate(note.updated_at)}
              </span>
            </button>
          ))}
        </nav>
      </aside>

      <section className="flex min-h-screen min-w-0 flex-col">
        <header className="flex min-h-16 flex-wrap items-center gap-3 border-b border-line bg-white px-4 py-3">
          <input
            className="min-w-0 flex-1 bg-transparent text-xl font-semibold outline-none"
            disabled={!selectedNote}
            onChange={(event) => setDraftTitle(event.target.value)}
            placeholder="Untitled"
            value={draftTitle}
          />
          <div className="flex items-center border border-line p-1">
            <button
              className={`px-3 py-1 text-sm font-medium ${viewMode === "edit" ? "bg-ink text-white" : "text-ink"}`}
              onClick={() => setViewMode("edit")}
              type="button"
            >
              Edit
            </button>
            <button
              className={`px-3 py-1 text-sm font-medium ${viewMode === "preview" ? "bg-ink text-white" : "text-ink"}`}
              onClick={() => setViewMode("preview")}
              type="button"
            >
              Preview
            </button>
          </div>
          <button
            className="flex items-center gap-2 border border-line px-3 py-2 text-sm font-semibold text-ink hover:border-moss disabled:opacity-50"
            disabled={!selectedNote || !isDirty || isBusy}
            onClick={handleSaveNote}
            type="button"
          >
            <Save size={16} />
            Save
          </button>
          <button
            className="border border-line p-2 text-clay hover:border-clay disabled:opacity-50"
            disabled={!selectedNote || isBusy}
            onClick={handleDeleteNote}
            title="Delete"
            type="button"
          >
            <Trash2 size={17} />
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-auto p-4">
          {selectedNote ? (
            viewMode === "edit" ? (
              <CodeMirror
                basicSetup={{ lineNumbers: true, foldGutter: false }}
                extensions={markdownExtensions}
                onChange={setDraftBody}
                value={draftBody}
              />
            ) : (
              <article className="markdown-preview min-h-[360px] border border-line bg-white p-5">
                <ReactMarkdown>{draftBody || " "}</ReactMarkdown>
              </article>
            )
          ) : (
            <div className="flex min-h-[360px] items-center justify-center border border-line bg-white text-moss">
              <FileText size={18} />
            </div>
          )}
        </div>

        <footer className="flex min-h-12 items-center justify-between border-t border-line bg-white px-4 text-sm text-moss">
          <span>{selectedNote ? `Version ${selectedNote.version_number}` : "No note selected"}</span>
          <span>{isDirty ? "Unsaved" : message}</span>
        </footer>
      </section>

      <aside className="border-t border-line bg-white lg:border-l lg:border-t-0">
        <div className="flex h-16 items-center gap-2 border-b border-line px-4">
          <PanelRight size={17} className="text-clay" />
          <h2 className="text-sm font-semibold uppercase tracking-wide text-moss">Context</h2>
        </div>

        <div className="grid grid-cols-2 border-b border-line p-1">
          <button
            className={`px-3 py-2 text-sm font-medium ${contextTab === "links" ? "bg-ink text-white" : "text-ink"}`}
            onClick={() => setContextTab("links")}
            type="button"
          >
            Links
          </button>
          <button
            className={`px-3 py-2 text-sm font-medium ${contextTab === "versions" ? "bg-ink text-white" : "text-ink"}`}
            onClick={() => setContextTab("versions")}
            type="button"
          >
            Versions
          </button>
        </div>

        <div className="max-h-[calc(100vh-112px)] overflow-auto p-4">
          {contextTab === "links" ? (
            <div className="space-y-5">
              <section>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-moss">
                  Backlinks
                </h3>
                <div className="space-y-2">
                  {backlinks.map((link) => (
                    <button
                      className="block w-full border border-line px-3 py-2 text-left text-sm hover:border-moss"
                      key={link.id}
                      onClick={() => setSelectedNoteId(link.source_note_id)}
                      type="button"
                    >
                      {link.source_note_title}
                    </button>
                  ))}
                  {backlinks.length === 0 ? <p className="text-sm text-moss">None</p> : null}
                </div>
              </section>

              <section>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-moss">
                  Outgoing
                </h3>
                <div className="space-y-2">
                  {outgoingLinks.map((link) => (
                    <div className="border border-line px-3 py-2 text-sm" key={link.id}>
                      <div className="font-medium">{link.raw_title}</div>
                      <div className="mt-1 text-xs capitalize text-moss">{link.status}</div>
                    </div>
                  ))}
                  {outgoingLinks.length === 0 ? <p className="text-sm text-moss">None</p> : null}
                </div>
              </section>
            </div>
          ) : (
            <div className="space-y-2">
              {versions.map((version) => (
                <div className="border border-line p-3" key={version.id}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold">v{version.version_number}</p>
                      <p className="text-xs capitalize text-moss">{version.reason}</p>
                    </div>
                    <button
                      className="border border-line p-2 text-ink hover:border-clay hover:text-clay"
                      disabled={isBusy}
                      onClick={() => handleRestoreVersion(version.id)}
                      title="Restore"
                      type="button"
                    >
                      <RotateCcw size={15} />
                    </button>
                  </div>
                  <p className="mt-2 truncate text-sm">{version.title}</p>
                  <p className="mt-1 text-xs text-moss">{formatDate(version.created_at)}</p>
                </div>
              ))}
              {versions.length === 0 ? <p className="text-sm text-moss">None</p> : null}
            </div>
          )}
        </div>
      </aside>
    </main>
  );
}
