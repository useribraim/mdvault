"use client";

import CodeMirror from "@uiw/react-codemirror";
import { markdown } from "@codemirror/lang-markdown";
import { EditorView } from "@codemirror/view";
import {
  ChevronRight,
  Download,
  FileText,
  Folder as FolderIcon,
  LogOut,
  MoreHorizontal,
  PanelRight,
  Plus,
  RotateCcw,
  Save,
  Search,
  Settings,
  Trash2,
  X,
} from "lucide-react";
import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";

import {
  ApiError,
  api,
  type Backlink,
  type Folder as VaultFolder,
  type Note,
  type NoteLink,
  type NoteVersion,
  type SearchResult,
  type User,
} from "@/lib/api";

type AuthMode = "login" | "register";
type ViewMode = "edit" | "preview";
type ContextTab = "links" | "versions";
type FolderSelection = "all" | "unfiled" | string;
type FolderNode = VaultFolder & { children: FolderNode[] };

const tokenStorageKey = "mdvault.token";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function buildFolderTree(folders: VaultFolder[]): FolderNode[] {
  const nodesById = new Map<string, FolderNode>();
  const roots: FolderNode[] = [];

  folders.forEach((folder) => {
    nodesById.set(folder.id, { ...folder, children: [] });
  });

  folders.forEach((folder) => {
    const node = nodesById.get(folder.id);
    if (!node) {
      return;
    }

    const parent = folder.parent_id ? nodesById.get(folder.parent_id) : null;
    if (parent) {
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  });

  const sortNodes = (nodes: FolderNode[]) => {
    nodes.sort((first, second) => first.name.localeCompare(second.name));
    nodes.forEach((node) => sortNodes(node.children));
  };
  sortNodes(roots);

  return roots;
}

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("strong-password");
  const [folders, setFolders] = useState<VaultFolder[]>([]);
  const [selectedFolderId, setSelectedFolderId] = useState<FolderSelection>("all");
  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [draftBody, setDraftBody] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("edit");
  const [contextTab, setContextTab] = useState<ContextTab>("links");
  const [isContextOpen, setIsContextOpen] = useState(false);
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
  const selectedFolder = useMemo(
    () => folders.find((folder) => folder.id === selectedFolderId) ?? null,
    [folders, selectedFolderId],
  );
  const folderTree = useMemo(() => buildFolderTree(folders), [folders]);
  const filteredNotes = useMemo(() => {
    if (searchQuery.trim()) {
      return searchResults.map((result) => result.note);
    }

    if (selectedFolderId === "all") {
      return notes;
    }

    if (selectedFolderId === "unfiled") {
      return notes.filter((note) => note.folder_id === null);
    }

    return notes.filter((note) => note.folder_id === selectedFolderId);
  }, [notes, searchQuery, searchResults, selectedFolderId]);

  const isDirty = selectedNote
    ? selectedNote.title !== draftTitle || selectedNote.body_markdown !== draftBody
    : false;

  const markdownExtensions = useMemo(() => [markdown(), EditorView.lineWrapping], []);

  const setSession = useCallback((nextToken: string, nextUser: User) => {
    localStorage.setItem(tokenStorageKey, nextToken);
    setToken(nextToken);
    setUser(nextUser);
  }, []);

  const clearSession = useCallback(() => {
    localStorage.removeItem(tokenStorageKey);
    setToken(null);
    setUser(null);
    setFolders([]);
    setSelectedFolderId("all");
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

  const loadFolders = useCallback(async (activeToken: string) => {
    const loadedFolders = await api.listFolders(activeToken);
    setFolders(loadedFolders);
  }, []);

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
        return Promise.all([loadNotes(storedToken), loadFolders(storedToken)]);
      })
      .catch(() => {
        clearSession();
      });
  }, [clearSession, loadFolders, loadNotes, setSession]);

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
      await Promise.all([loadNotes(loginResponse.access_token), loadFolders(loginResponse.access_token)]);
    });
  }

  async function handleCreateNote() {
    if (!token) {
      return;
    }

    await runAction(async () => {
      const folderId =
        selectedFolderId !== "all" && selectedFolderId !== "unfiled" ? selectedFolderId : null;
      const note = await api.createNote(token, "Untitled", "", folderId);
      await loadNotes(token, note.id);
      setViewMode("edit");
    });
  }

  function handleSelectFolder(nextFolderId: FolderSelection) {
    setSelectedFolderId(nextFolderId);
    setSearchQuery("");
    setSearchResults([]);

    const matchingNotes =
      nextFolderId === "all"
        ? notes
        : nextFolderId === "unfiled"
          ? notes.filter((note) => note.folder_id === null)
          : notes.filter((note) => note.folder_id === nextFolderId);
    setSelectedNoteId(matchingNotes[0]?.id ?? null);
  }

  async function handleCreateFolder() {
    if (!token) {
      return;
    }

    const folderName = window.prompt("Folder name");
    const trimmedName = folderName?.trim();
    if (!trimmedName) {
      return;
    }

    await runAction(async () => {
      const parentId =
        selectedFolderId !== "all" && selectedFolderId !== "unfiled" ? selectedFolderId : null;
      const folder = await api.createFolder(token, trimmedName, parentId);
      setFolders((currentFolders) => [...currentFolders, folder]);
      setSelectedFolderId(folder.id);
      setSearchQuery("");
      setSearchResults([]);
      setMessage("Folder created");
    });
  }

  async function handleMoveSelectedNote(nextFolderId: string) {
    if (!token || !selectedNote) {
      return;
    }

    const folderId = nextFolderId || null;
    await runAction(async () => {
      const movedNote = await api.updateNote(token, selectedNote.id, { folder_id: folderId });
      setNotes((currentNotes) =>
        currentNotes.map((note) => (note.id === movedNote.id ? movedNote : note)),
      );
      setSearchResults((currentResults) =>
        currentResults.map((result) =>
          result.note.id === movedNote.id ? { ...result, note: movedNote } : result,
        ),
      );
      setSelectedFolderId(folderId ?? "unfiled");
      setMessage("Moved");
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

  const listLabel = searchQuery.trim()
    ? "Search results"
    : selectedFolderId === "all"
      ? "Notes"
      : selectedFolderId === "unfiled"
        ? "Unfiled"
        : selectedFolder?.name ?? "Notes";

  function renderFolderNode(folder: FolderNode, depth = 0): ReactNode {
    return (
      <div key={folder.id}>
        <button
          className={`flex w-full items-center gap-2 rounded-md py-1.5 pr-2 text-left text-[15px] transition ${
            selectedFolderId === folder.id
              ? "bg-[#e2e2e2] text-[#1f1f1f]"
              : "text-[#4c4c4c] hover:bg-[#ededed]"
          }`}
          onClick={() => handleSelectFolder(folder.id)}
          style={{ paddingLeft: `${12 + depth * 16}px` }}
          type="button"
        >
          <ChevronRight size={15} strokeWidth={1.8} className="shrink-0 text-[#8a8a8a]" />
          <span className="truncate">{folder.name}</span>
        </button>
        {folder.children.map((childFolder) => renderFolderNode(childFolder, depth + 1))}
      </div>
    );
  }

  if (!token || !user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-paper px-4 py-8">
        <section className="w-full max-w-sm rounded-2xl border border-line bg-[#fffdf7] p-6 shadow-[0_24px_80px_rgba(21,25,20,0.10)]">
          <div className="mb-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">mdvault</p>
            <h1 className="mt-1 text-3xl font-semibold text-ink">Markdown workspace</h1>
          </div>

          <div className="mb-4 grid grid-cols-2 rounded-full bg-[#eee6d4] p-1">
            <button
              className={`rounded-full px-3 py-2 text-sm font-medium ${authMode === "login" ? "bg-night text-white" : "text-ink"}`}
              onClick={() => setAuthMode("login")}
              type="button"
            >
              Login
            </button>
            <button
              className={`rounded-full px-3 py-2 text-sm font-medium ${authMode === "register" ? "bg-night text-white" : "text-ink"}`}
              onClick={() => setAuthMode("register")}
              type="button"
            >
              Register
            </button>
          </div>

          <label className="mb-3 block text-sm font-medium text-ink">
            Email
            <input
              className="mt-1 w-full rounded-lg border border-line bg-paper px-3 py-2 outline-none focus:border-moss"
              onChange={(event) => setEmail(event.target.value)}
              type="email"
              value={email}
            />
          </label>
          <label className="mb-4 block text-sm font-medium text-ink">
            Password
            <input
              className="mt-1 w-full rounded-lg border border-line bg-paper px-3 py-2 outline-none focus:border-moss"
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              value={password}
            />
          </label>

          <button
            className="flex w-full items-center justify-center gap-2 rounded-full bg-night px-3 py-2.5 font-semibold text-white disabled:opacity-60"
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
    <main className="relative grid min-h-screen grid-cols-1 bg-white text-ink lg:grid-cols-[344px_minmax(0,1fr)]">
      <aside className="flex min-h-screen flex-col border-r border-[#d6d6d6] bg-[#f7f7f7] text-[#3f3f3f]">
        <div className="flex h-[66px] items-center gap-2 border-b border-[#dcdcdc] px-5">
          <span className="h-3.5 w-3.5 rounded-full bg-[#ff5f57]" />
          <span className="h-3.5 w-3.5 rounded-full bg-[#ffbd2e]" />
          <span className="h-3.5 w-3.5 rounded-full bg-[#28c840]" />
        </div>

        <div className="px-7 pt-5">
          <div className="mb-7 flex items-center justify-between">
            <FolderIcon size={24} strokeWidth={1.6} className="text-[#6f6f6f]" />
            <button
              className="rounded-md p-1.5 text-[#6f6f6f] hover:bg-[#e7e7e7]"
              disabled={isBusy}
              onClick={handleExportNotes}
              title="Export notes"
              type="button"
            >
              <Download size={18} strokeWidth={1.7} />
            </button>
          </div>

          <div className="mb-5 flex items-center rounded-lg bg-white/70 px-2.5">
            <Search size={15} className="text-[#8a8a8a]" />
            <input
              className="w-full bg-transparent px-2 py-1.5 text-sm text-[#3f3f3f] outline-none placeholder:text-[#9a9a9a]"
              onChange={(event) => handleSearch(event.target.value)}
              placeholder="Search"
              value={searchQuery}
            />
          </div>
        </div>

        <div className="mb-4 px-5">
          <div className="mb-1 flex items-center justify-between px-2">
            <span className="text-[13px] font-medium uppercase tracking-wide text-[#777]">Folders</span>
            <button
              className="rounded-md p-1 text-[#6f6f6f] hover:bg-[#e7e7e7] disabled:opacity-60"
              disabled={isBusy}
              onClick={handleCreateFolder}
              title="New folder"
              type="button"
            >
              <Plus size={15} />
            </button>
          </div>
          <div className="space-y-1">
            <button
              className={`flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-left text-[15px] ${
                selectedFolderId === "all" ? "bg-[#e2e2e2] text-[#1f1f1f]" : "text-[#4c4c4c] hover:bg-[#ededed]"
              }`}
              onClick={() => handleSelectFolder("all")}
              type="button"
            >
              <FolderIcon size={15} strokeWidth={1.8} className="text-[#8a8a8a]" />
              All notes
            </button>
            <button
              className={`flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-left text-[15px] ${
                selectedFolderId === "unfiled" ? "bg-[#e2e2e2] text-[#1f1f1f]" : "text-[#4c4c4c] hover:bg-[#ededed]"
              }`}
              onClick={() => handleSelectFolder("unfiled")}
              type="button"
            >
              <FolderIcon size={15} strokeWidth={1.8} className="text-[#8a8a8a]" />
              Unfiled
            </button>
            {folderTree.map((folder) => renderFolderNode(folder))}
          </div>
        </div>

        <div className="mb-2 flex items-center justify-between px-7">
          <div className="flex min-w-0 items-center gap-2 text-[15px] text-[#555]">
            <ChevronRight size={17} strokeWidth={1.8} className="shrink-0 text-[#8a8a8a]" />
            <span className="truncate">{listLabel}</span>
          </div>
          <button
            className="rounded-md p-1.5 text-[#6f6f6f] hover:bg-[#e7e7e7] disabled:opacity-60"
            disabled={isBusy}
            onClick={handleCreateNote}
            title="New note"
            type="button"
          >
            <Plus size={17} />
          </button>
        </div>

        <nav className="min-h-0 flex-1 space-y-1 overflow-auto px-5 pb-5">
          {filteredNotes.map((note) => (
            <button
              className={`block w-full rounded-md px-4 py-2.5 text-left text-[15px] transition ${
                selectedNoteId === note.id
                  ? "bg-[#e2e2e2] text-[#1f1f1f]"
                  : "bg-transparent text-[#4c4c4c] hover:bg-[#ededed]"
              }`}
              key={note.id}
              onClick={() => setSelectedNoteId(note.id)}
              type="button"
            >
              <span className="block truncate">{note.title}</span>
              <span className="mt-0.5 block truncate text-xs text-[#777]">
                v{note.version_number} · {formatDate(note.updated_at)}
              </span>
            </button>
          ))}
        </nav>

        <div className="flex h-[66px] items-center justify-between border-t border-[#dcdcdc] px-7">
          <span className="text-[15px] text-[#333]">Obsidian Vault</span>
          <button
            className="rounded-md p-1.5 text-[#6f6f6f] hover:bg-[#e7e7e7]"
            onClick={clearSession}
            title="Log out"
            type="button"
          >
            <Settings size={20} strokeWidth={1.7} />
          </button>
        </div>
      </aside>

      <section className="flex min-h-screen min-w-0 flex-col">
        <header className="grid h-[58px] grid-cols-[1fr_auto_1fr] items-center border-b border-[#dedede] bg-white px-5">
          <div />
          <div className="min-w-0 max-w-md truncate text-center text-[15px] font-medium text-[#151515]">
            {draftTitle || "Untitled"}
          </div>
          <div className="flex items-center justify-end gap-1.5">
            <button
              className="rounded-md p-1.5 text-[#555] hover:bg-[#f0f0f0] disabled:opacity-40"
              disabled={!selectedNote || !isDirty || isBusy}
              onClick={handleSaveNote}
              title="Save"
              type="button"
            >
              <Save size={18} strokeWidth={1.7} />
            </button>
            <button
              className="rounded-md p-1.5 text-[#555] hover:bg-[#f0f0f0] disabled:opacity-40"
              disabled={!selectedNote}
              onClick={() => setIsContextOpen((currentValue) => !currentValue)}
              title="Context"
              type="button"
            >
              <PanelRight size={19} strokeWidth={1.7} />
            </button>
            <button
              className="rounded-md p-1.5 text-[#555] hover:bg-[#f0f0f0]"
              title="More"
              type="button"
            >
              <MoreHorizontal size={20} strokeWidth={1.8} />
            </button>
          </div>
        </header>

        <div className="flex min-h-0 flex-1 flex-col overflow-auto bg-white">
          <div className="mx-auto w-full max-w-[920px] px-10 pb-10 pt-12">
          <input
            className="mb-5 w-full bg-transparent text-[34px] font-bold leading-tight outline-none"
            disabled={!selectedNote}
            onChange={(event) => setDraftTitle(event.target.value)}
            placeholder="Untitled"
            value={draftTitle}
          />
          <div className="mb-5 flex items-center gap-2 text-sm text-[#666]">
            <span>Folder</span>
            <select
              className="rounded-md border border-[#d8d8d8] bg-white px-2 py-1 outline-none focus:border-[#9a9a9a]"
              disabled={!selectedNote || isBusy}
              onChange={(event) => handleMoveSelectedNote(event.target.value)}
              value={selectedNote?.folder_id ?? ""}
            >
              <option value="">Unfiled</option>
              {folders.map((folder) => (
                <option key={folder.id} value={folder.id}>
                  {folder.name}
                </option>
              ))}
            </select>
          </div>

          {selectedNote ? (
            viewMode === "edit" ? (
              <div className="min-h-[520px]">
                <CodeMirror
                  basicSetup={{ lineNumbers: false, foldGutter: false }}
                  extensions={markdownExtensions}
                  onChange={setDraftBody}
                  value={draftBody}
                />
              </div>
            ) : (
              <article className="markdown-preview min-h-[520px] text-[18px] leading-8">
                <ReactMarkdown>{draftBody || " "}</ReactMarkdown>
              </article>
            )
          ) : (
            <div className="flex min-h-[520px] items-center justify-center text-[#777]">
              <FileText size={18} />
            </div>
          )}
          </div>
        </div>

        <footer className="flex h-[66px] items-center justify-end gap-5 border-t border-[#dedede] bg-white px-8 text-sm text-[#555]">
          <span>{selectedNote ? `Version ${selectedNote.version_number}` : "No note selected"}</span>
          <span>{isDirty ? "Unsaved" : message}</span>
        </footer>
      </section>

      {isContextOpen ? (
        <button
          aria-label="Close context overlay"
          className="fixed inset-0 z-10 bg-ink/10"
          onClick={() => setIsContextOpen(false)}
          type="button"
        />
      ) : null}

      {isContextOpen ? (
        <aside className="fixed inset-y-0 right-0 z-20 w-full max-w-[360px] border-l border-line bg-[#fffdf7] shadow-[0_24px_90px_rgba(21,25,20,0.18)]">
          <div className="flex h-16 items-center justify-between border-b border-line px-4">
            <div className="flex items-center gap-2">
              <PanelRight size={17} className="text-clay" />
              <h2 className="text-sm font-semibold uppercase tracking-wide text-moss">Context</h2>
            </div>
            <button
              className="rounded-full border border-line p-2 text-ink hover:border-moss"
              onClick={() => setIsContextOpen(false)}
              title="Close context"
              type="button"
            >
              <X size={16} />
            </button>
          </div>

          <div className="grid grid-cols-2 border-b border-line bg-paper p-1">
            <button
              className={`rounded-full px-3 py-2 text-sm font-medium ${contextTab === "links" ? "bg-night text-white" : "text-ink"}`}
              onClick={() => setContextTab("links")}
              type="button"
            >
              Links
            </button>
            <button
              className={`rounded-full px-3 py-2 text-sm font-medium ${contextTab === "versions" ? "bg-night text-white" : "text-ink"}`}
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
                        className="block w-full rounded-xl border border-line bg-white/60 px-3 py-2 text-left text-sm hover:border-moss"
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
                      <div className="rounded-xl border border-line bg-white/60 px-3 py-2 text-sm" key={link.id}>
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
                  <div className="rounded-xl border border-line bg-white/60 p-3" key={version.id}>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold">v{version.version_number}</p>
                        <p className="text-xs capitalize text-moss">{version.reason}</p>
                      </div>
                      <button
                        className="rounded-full border border-line p-2 text-ink hover:border-clay hover:text-clay"
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
      ) : null}
    </main>
  );
}
