export const CONVEX_URL: string | undefined = import.meta.env.VITE_CONVEX_URL;
export const TELEGRAM_BOT: string =
  import.meta.env.VITE_TELEGRAM_BOT ?? "your_bot_here";
export const convexConfigured = Boolean(CONVEX_URL);

export function navigate(path: string): void {
  window.location.hash = path;
}
