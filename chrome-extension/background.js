const API_URL = "https://yt-dlp.odieserver.com/download";

chrome.action.onClicked.addListener(async (tab) => {
  const url = tab.url;

  if (!url || url.startsWith("chrome://") || url.startsWith("chrome-extension://")) {
    setBadge("X", "#f56565");
    return;
  }

  try {
    const domain = new URL(url).hostname;
    const cookies = await getCookiesForDomain(domain);

    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ urls: [url], cookies }),
    });

    if (response.ok) {
      setBadge("✓", "#48bb78");
    } else {
      const data = await response.json().catch(() => ({}));
      console.error("yt-dlp-web error:", data.error || response.status);
      setBadge("!", "#f6ad55");
    }
  } catch (error) {
    console.error("Network error:", error);
    setBadge("!", "#f56565");
  }
});

async function getCookiesForDomain(domain) {
  const cookies = await chrome.cookies.getAll({ domain });

  // Also get cookies for parent domain (e.g., .example.com for www.example.com)
  const parts = domain.split(".");
  let parentCookies = [];
  if (parts.length > 2) {
    const parent = parts.slice(1).join(".");
    parentCookies = await chrome.cookies.getAll({ domain: parent });
  }

  const all = [...cookies, ...parentCookies];
  const seen = new Set();
  const unique = [];

  for (const c of all) {
    const key = `${c.domain}|${c.name}|${c.path}`;
    if (!seen.has(key)) {
      seen.add(key);
      unique.push({
        domain: c.domain,
        name: c.name,
        value: c.value,
        path: c.path,
        secure: c.secure,
        httpOnly: c.httpOnly,
        expirationDate: c.expirationDate || 0,
      });
    }
  }

  return unique;
}

function setBadge(text, color) {
  chrome.action.setBadgeText({ text });
  chrome.action.setBadgeBackgroundColor({ color });
  setTimeout(() => chrome.action.setBadgeText({ text: "" }), 3000);
}
