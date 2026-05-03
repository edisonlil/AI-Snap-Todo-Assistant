import "./styles.css";

import { faqItems, homeContent, siteMeta } from "./site.config.js";
import { buildFooter, buildHeader } from "./shared.js";

document.title = `${siteMeta.brand} - 截图驱动的 AI 待办工作台`;

const app = document.querySelector("#app");

app.innerHTML = `
  <div class="site-shell">
    ${buildHeader("home")}
    <main class="home-main">
      <section class="hero-section reveal">
        <div class="hero-copy">
          <span class="hero-badge">${homeContent.hero.label}</span>
          <h1>${homeContent.hero.title}</h1>
          <p class="hero-summary">${homeContent.hero.summary}</p>
          <div class="hero-actions">
            <a class="button button-primary" href="${homeContent.hero.primaryHref}">${homeContent.hero.primaryCta}</a>
            <a class="button button-secondary" href="${homeContent.hero.secondaryHref}">${homeContent.hero.secondaryCta}</a>
          </div>
        </div>
        <div class="hero-stats">
          ${homeContent.stats
            .map(
              (item) => `
                <div class="stat-card">
                  <strong>${item.value}</strong>
                  <span>${item.label}</span>
                </div>
              `,
            )
            .join("")}
        </div>
      </section>

      <section class="section-block section-split intro-section reveal">
        <div class="section-intro">
          <span class="eyebrow">Why Chattodo</span>
          <h1>为问题处理团队设计，不是又一个泛用清单</h1>
        </div>
        <div class="value-grid">
          ${homeContent.values
            .map(
              (item) => `
                <article class="value-card">
                  <h3>${item.title}</h3>
                  <p>${item.body}</p>
                </article>
              `,
            )
            .join("")}
        </div>
      </section>

      <section class="section-block workflow-section reveal" id="workflow">
        <div class="section-intro">
          <span class="eyebrow">Workflow</span>
          <h2>从问题进入视野，到经验留在团队里</h2>
        </div>
        <div class="workflow-list">
          ${homeContent.workflow
            .map(
              (item) => `
                <article class="workflow-card">
                  <span class="step-no">${item.step}</span>
                  <h3>${item.title}</h3>
                  <p>${item.body}</p>
                </article>
              `,
            )
            .join("")}
        </div>
      </section>

      <section class="section-block feature-section reveal" id="features">
        <div class="section-intro">
          <span class="eyebrow">Core Features</span>
          <h2>把分散工具里的上下文收回到待办本身</h2>
        </div>
        <div class="feature-grid">
          ${homeContent.capabilities
            .map(
              (item, index) => `
                <article class="feature-card">
                  <span class="card-index">${String(index + 1).padStart(2, "0")}</span>
                  <div>
                    <h3>${item.title}</h3>
                    <p>${item.body}</p>
                  </div>
                </article>
              `,
            )
            .join("")}
        </div>
      </section>

      <section class="section-block audience-section reveal">
        <div class="section-intro">
          <span class="eyebrow">Built For</span>
          <h2>适合每天处理问题、验证和排障的人</h2>
        </div>
        <div class="audience-grid">
          ${homeContent.audiences
            .map(
              (item) => `
                <article class="audience-card">
                  <h3>${item.title}</h3>
                  <p>${item.body}</p>
                </article>
              `,
            )
            .join("")}
        </div>
      </section>

      <section class="section-block scenario-band reveal">
        <div class="section-intro">
          <span class="eyebrow">Scenarios</span>
          <h2>典型使用场景</h2>
        </div>
        <div class="scenario-list">
          ${homeContent.scenarios.map((item) => `<p>${item}</p>`).join("")}
        </div>
      </section>

      <section class="section-block download-band reveal" id="download">
        <div>
          <span class="eyebrow">Start</span>
          <h2>先从一次截图创建待办开始</h2>
        </div>
        <div class="download-grid">
          ${homeContent.downloadCards
            .map(
              (item) => `
                <article class="download-card">
                  <h3>${item.title}</h3>
                  <p>${item.body}</p>
                  <a href="${item.href}">${item.cta}</a>
                </article>
              `,
            )
            .join("")}
        </div>
      </section>

      <section class="section-block reveal">
        <div class="section-intro">
          <span class="eyebrow">FAQ</span>
          <h2>常见问题</h2>
        </div>
        <div class="faq-preview-grid">
          ${faqItems
            .map(
              (item) => `
                <article class="faq-preview-card">
                  <h3>${item.question}</h3>
                  <p>${item.answer}</p>
                </article>
              `,
            )
            .join("")}
        </div>
      </section>
    </main>
    ${buildFooter()}
  </div>
`;
