const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type User = {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
};

export type Note = {
  id: string;
  folder_id: string | null;
  title: string;
  body_markdown: string;
  version_number: number;
  created_at: string;
  updated_at: string;
};

export type Folder = {
  id: string;
  parent_id: string | null;
  name: string;
  created_at: string;
  updated_at: string;
};

export type NoteLink = {
  id: string;
  source_note_id: string;
  target_note_id: string | null;
  raw_title: string;
  status: "resolved" | "unresolved" | "ambiguous";
  created_at: string;
  updated_at: string;
};

export type Backlink = {
  id: string;
  source_note_id: string;
  source_note_title: string;
  raw_title: string;
  status: string;
  created_at: string;
};

export type NoteVersion = {
  id: string;
  note_id: string;
  title: string;
  body_markdown: string;
  version_number: number;
  reason: "created" | "updated" | "restored";
  created_at: string;
};

export type SearchResult = {
  note: Note;
  rank: number;
};

type RequestOptions = {
  token?: string | null;
  method?: string;
  body?: unknown;
};

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = data?.detail;
    const message =
      typeof detail?.message === "string"
        ? detail.message
        : `Request failed with status ${response.status}`;
    throw new ApiError(response.status, message);
  }

  return data as T;
}

async function download(path: string, token: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      Accept: "application/zip",
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const detail = data?.detail;
    const message =
      typeof detail?.message === "string"
        ? detail.message
        : `Request failed with status ${response.status}`;
    throw new ApiError(response.status, message);
  }

  return response.blob();
}

export const api = {
  register(email: string, password: string) {
    return request<User>("/auth/register", {
      method: "POST",
      body: { email, password },
    });
  },
  login(email: string, password: string) {
    return request<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      body: { email, password },
    });
  },
  me(token: string) {
    return request<User>("/me", { token });
  },
  listNotes(token: string) {
    return request<Note[]>("/notes", { token });
  },
  listFolders(token: string) {
    return request<Folder[]>("/folders", { token });
  },
  createFolder(token: string, name: string, parent_id: string | null = null) {
    return request<Folder>("/folders", {
      token,
      method: "POST",
      body: { name, parent_id },
    });
  },
  createNote(token: string, title: string, body_markdown = "", folder_id: string | null = null) {
    return request<Note>("/notes", {
      token,
      method: "POST",
      body: { title, body_markdown, folder_id },
    });
  },
  updateNote(token: string, noteId: string, body: Partial<Pick<Note, "title" | "body_markdown" | "folder_id">>) {
    return request<Note>(`/notes/${noteId}`, {
      token,
      method: "PATCH",
      body,
    });
  },
  deleteNote(token: string, noteId: string) {
    return request<void>(`/notes/${noteId}`, {
      token,
      method: "DELETE",
    });
  },
  search(token: string, query: string) {
    return request<SearchResult[]>(`/search?q=${encodeURIComponent(query)}`, { token });
  },
  outgoingLinks(token: string, noteId: string) {
    return request<NoteLink[]>(`/notes/${noteId}/outgoing-links`, { token });
  },
  backlinks(token: string, noteId: string) {
    return request<Backlink[]>(`/notes/${noteId}/backlinks`, { token });
  },
  versions(token: string, noteId: string) {
    return request<NoteVersion[]>(`/notes/${noteId}/versions`, { token });
  },
  restoreVersion(token: string, noteId: string, versionId: string) {
    return request<Note>(`/notes/${noteId}/versions/${versionId}/restore`, {
      token,
      method: "POST",
    });
  },
  exportNotes(token: string) {
    return download("/export.zip", token);
  },
};
