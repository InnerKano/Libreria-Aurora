export const resolveMediaUrl = (raw) => {
  if (!raw) return "";

  if (typeof raw !== "string") return "";

  // Absolute URL already
  if (raw.startsWith("http://") || raw.startsWith("https://")) return raw;

  // If backend returns a relative path (e.g. Cloudinary 'image/upload/...'), allow a configurable base
  const base =
    process.env.REACT_APP_MEDIA_BASE_URL ||
    process.env.REACT_APP_CLOUDINARY_BASE_URL ||
    "";

  if (base && (raw.startsWith("image/") || raw.startsWith("/image/"))) {
    const normalizedBase = base.endsWith("/") ? base : `${base}/`;
    const normalizedRaw = raw.startsWith("/") ? raw.slice(1) : raw;
    return `${normalizedBase}${normalizedRaw}`;
  }

  return raw;
};

export const getBookCoverSrc = (book) => {
  const raw = book?.portada_url || book?.portada;
  return resolveMediaUrl(raw);
};
