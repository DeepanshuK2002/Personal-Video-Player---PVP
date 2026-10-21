// Runs once when the Next.js server boots (see Next.js "instrumentation").
// We use it to start the background hentairead trending refresher, which keeps
// the trending list fresh on a 6-hour cadence without needing external cron.
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { startTrendingRefresher } = await import("./lib/providers/scheduler");
    startTrendingRefresher();
  }
}
