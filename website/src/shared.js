import { docsNav, siteMeta } from "./site.config.js";

export function getBasePath() {
  return document.body.dataset.base || ".";
}

export function pageLink(path) {
  return `${getBasePath()}/${path}`.replace("/./", "/");
}

export function buildHeader(current) {
  const docsHref = current === "home" ? "./docs/index.html" : "../docs/index.html";
  const homeHref = current === "home" ? "./index.html" : "../index.html";
  const featureHref = current === "home" ? "#features" : "../index.html#features";
  const downloadHref =
    current === "home" ? "./docs/installation.html#download" : "./installation.html#download";

  return `
    <header class="site-header">
      <a class="brand-lockup" href="${homeHref}">
        <span class="brand-orb"></span>
        <span>
          <strong>${siteMeta.brand}</strong>
          <small>${siteMeta.badge}</small>
        </span>
      </a>
      <nav class="top-nav" aria-label="主导航">
        <a href="${featureHref}">产品特性</a>
        <a href="${docsHref}">使用文档</a>
        <a href="${downloadHref}">下载/获取</a>
      </nav>
    </header>
  `;
}

export function buildFooter() {
  return `
    <footer class="site-footer">
      <div>
        <strong>${siteMeta.brand}</strong>
        <p>${siteMeta.description}</p>
      </div>
      <p>${siteMeta.footerNote}</p>
    </footer>
  `;
}

export function buildDocsSidebar(currentKey) {
  return `
    <aside class="docs-sidebar">
      <div class="docs-sidebar-head">
        <span class="eyebrow">Documentation</span>
        <h2>基础用户文档</h2>
        <p>先完成安装、配置和第一条待办闭环，再逐步引入更复杂的团队流程。</p>
      </div>
      <nav class="docs-sidebar-nav" aria-label="文档导航">
        ${docsNav
          .map(
            (item) => `
              <a class="${item.key === currentKey ? "active" : ""}" href="./${item.href}">
                <span>${item.title}</span>
              </a>
            `,
          )
          .join("")}
      </nav>
    </aside>
  `;
}

export function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function renderBlocks(blocks) {
  return blocks
    .map((block) => {
      if (block.type === "html") {
        return block.html;
      }

      if (block.type === "list") {
        return `<ul class="prose-list">${block.items.map((item) => `<li>${item}</li>`).join("")}</ul>`;
      }

      if (block.type === "code") {
        return `
          <div class="code-block">
            <div class="code-label">${block.language}</div>
            <pre><code>${escapeHtml(block.code)}</code></pre>
          </div>
        `;
      }

      if (block.type === "callout") {
        return `
          <div class="callout callout-${block.tone || "muted"}">
            <strong>${block.title}</strong>
            <p>${block.text}</p>
          </div>
        `;
      }

      if (block.type === "faq") {
        return `
          <div class="faq-stack">
            ${block.items
              .map(
                (item) => `
                  <details class="faq-item">
                    <summary>${item.question}</summary>
                    <p>${item.answer}</p>
                  </details>
                `,
              )
              .join("")}
          </div>
        `;
      }

      return "";
    })
    .join("");
}
