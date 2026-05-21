import "./styles.css";

import { docsPages, siteMeta } from "./site.config.js";
import { buildDocsSidebar, buildFooter, buildHeader, renderBlocks } from "./shared.js";

const pageKey = document.body.dataset.page || "index";
const page = docsPages[pageKey] || docsPages.index;
const app = document.querySelector("#app");

document.title = `${page.title} - ${siteMeta.brand} 文档`;

app.innerHTML = `
  <div class="site-shell docs-shell">
    ${buildHeader("docs")}
    <main class="docs-layout">
      ${buildDocsSidebar(pageKey)}
      <section class="docs-content">
        <div class="docs-page-head">
          <div>
            <span class="eyebrow">${page.eyebrow}</span>
            <h1>${page.title}</h1>
            <p>${page.summary}</p>
          </div>
          <nav class="anchor-row" aria-label="页面章节">
            ${page.sections.map((section) => `<a href="#${section.id}">${section.title}</a>`).join("")}
          </nav>
        </div>
        ${page.sections
          .map(
            (section) => `
              <article class="doc-section" id="${section.id}">
                <div class="doc-section-head">
                  <span class="section-kicker">${section.id}</span>
                  <h2>${section.title}</h2>
                </div>
                <div class="prose">
                  ${renderBlocks(section.blocks)}
                </div>
              </article>
            `,
          )
          .join("")}
      </section>
    </main>
    ${buildFooter()}
  </div>
`;
