import "./styles.css";

import { faqItems, homeContent, siteMeta } from "./site.config.js";
import { buildFooter, buildHeader } from "./shared.js";

document.title = `${siteMeta.brand} · 官网`;

const app = document.querySelector("#app");

app.innerHTML = `
  <div class="site-shell">
    ${buildHeader("home")}
    <main>
      <section class="hero-grid">
        <div class="hero-copy reveal">
          <span class="hero-badge">${siteMeta.badge}</span>
          <h1>把截图变成真正能推进的任务上下文。</h1>
          <p class="hero-summary">
            ${siteMeta.brand} 把聊天记录、报错现场和后续动作收拢到一条连续时间线里，
            让技术支持、售后、实施和交付团队不再反复整理同一件事。
          </p>
          <div class="hero-actions">
            <a class="button button-primary" href="./docs/installation.html#download">下载/获取</a>
            <a class="button button-secondary" href="./docs/index.html">查看文档</a>
          </div>
          <div class="hero-stats">
            ${homeContent.heroStats
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
        </div>
      </section>

      <section class="section-block reveal">
        <div class="section-intro">
          <span class="eyebrow">Why Chattodo</span>
          <h2>截图工具解决采集，待办工具解决记录，Chattodo 解决的是持续推进。</h2>
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

      <section class="section-block reveal" id="features">
        <div class="section-intro">
          <span class="eyebrow">Core Features</span>
          <h2>首版官网聚焦五类核心能力，全部来自当前项目已有事实能力。</h2>
        </div>
        <div class="feature-grid">
          ${homeContent.features
            .map(
              (item) => `
                <article class="feature-card feature-${item.accent}">
                  <span class="card-index">0${homeContent.features.indexOf(item) + 1}</span>
                  <h3>${item.title}</h3>
                  <p>${item.body}</p>
                </article>
              `,
            )
            .join("")}
        </div>
      </section>

      <section class="section-block reveal">
        <div class="section-intro">
          <span class="eyebrow">Workflow</span>
          <h2>一条适合现场团队的四步闭环。</h2>
        </div>
        <div class="workflow-grid">
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

      <section class="section-block reveal">
        <div class="section-intro">
          <span class="eyebrow">Built For</span>
          <h2>这些岗位最容易从 Chattodo 的时间线化工作流里受益。</h2>
        </div>
        <div class="audience-row">
          ${homeContent.audiences.map((item) => `<span>${item}</span>`).join("")}
        </div>
      </section>

      <section class="section-block reveal" id="download">
        <div class="section-intro">
          <span class="eyebrow">Download / Access</span>
          <h2>把下载安装和上手路径讲清楚，就能让它更像一款真正交付的软件。</h2>
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
          <h2>先把第一次接触这个产品时最容易问到的问题说清楚。</h2>
        </div>
        <div class="faq-preview-grid">
          ${faqItems
            .slice(0, 5)
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
