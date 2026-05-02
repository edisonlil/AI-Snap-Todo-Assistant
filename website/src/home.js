import "./styles.css";

import { faqItems, homeContent, siteMeta } from "./site.config.js";
import { buildFooter, buildHeader } from "./shared.js";

document.title = `${siteMeta.brand} · 官网`;

const app = document.querySelector("#app");

function renderProductDemo() {
  return `
    <div class="product-demo control-demo" aria-label="Chattodo Hub 工单管理界面示意">
      <div class="control-shot">
        <div class="control-titlebar">
          <div class="control-brand">
            <span class="control-logo"></span>
            <strong>Chattodo Hub</strong>
          </div>
          <div class="control-window-actions" aria-hidden="true">
            <span>-</span>
            <span>□</span>
            <span>×</span>
          </div>
        </div>
        <div class="control-workspace">
          <aside class="control-sidebar">
            <div class="control-nav-group">
              <p>业务管理</p>
              <span>项目管理</span>
              <span class="active">工单管理</span>
              <span>环境管理</span>
            </div>
            <div>
              <p>模型与规则</p>
              <span>模型供应商</span>
              <span>规则与调试</span>
            </div>
            <div>
              <p>运行与集成</p>
              <span>快捷键</span>
              <span>存储与日志</span>
              <span>脚本集成</span>
            </div>
            <small>提示: 如功能提示配置缺失，请从托盘图标进入这里完成设置。</small>
          </aside>
          <section class="control-main">
            <div class="control-main-head">
              <div>
                <h3>工单管理</h3>
                <p>查看打开中或已完成的工单，并在控制面板内查看 timeline 历史跟进详情。</p>
              </div>
              <button type="button">刷新列表</button>
            </div>
            <div class="control-table-card">
              <div class="control-filters">
                <span class="control-search">搜索工单标题</span>
                <span>已完成</span>
                <span>文档中心</span>
                <span>类型</span>
              </div>
              <div class="control-table">
                <div class="control-row control-head">
                  <span>工单标题</span>
                  <span>状态</span>
                  <span>项目</span>
                  <span>产品线</span>
                  <span>类型</span>
                  <span>更新时间</span>
                  <span>操作</span>
                </div>
                <div class="control-row">
                  <strong>在文档中心的全文检索中搜索固定字符...</strong>
                  <span class="done">已完成</span>
                  <span>2024北京市自来水集团有限...</span>
                  <span>文档中心</span>
                  <span>排查类</span>
                  <span>04-30 15:42</span>
                  <span>复制  详情</span>
                </div>
                <div class="control-row">
                  <strong>V7版本对接企业微信功能咨询</strong>
                  <span class="done">已完成</span>
                  <span>广州市瀚蓝环境股份有限公...</span>
                  <span>文档中心</span>
                  <span>咨询类</span>
                  <span>04-29 17:51</span>
                  <span>复制  详情</span>
                </div>
                <div class="control-row">
                  <strong>WPS 传统表格更新区域数据报错: In...</strong>
                  <span class="done">已完成</span>
                  <span>2025广东电网有限责任公司...</span>
                  <span>文档中心</span>
                  <span>排查类</span>
                  <span>04-29 17:49</span>
                  <span>复制  详情</span>
                </div>
                <div class="control-row">
                  <strong>WPS在线使用时频繁自动退出登录</strong>
                  <span class="done">已完成</span>
                  <span>2025广东中烟工业有限责任...</span>
                  <span>文档中心</span>
                  <span>排查类</span>
                  <span>04-27 17:49</span>
                  <span>复制  详情</span>
                </div>
                <div class="control-row">
                  <strong>智能文档API无法获取查询块内容</strong>
                  <span class="done">已完成</span>
                  <span>2024广州四三九九信息科技...</span>
                  <span>文档中心</span>
                  <span>排查类</span>
                  <span>04-23 02:40</span>
                  <span>复制  详情</span>
                </div>
              </div>
            </div>
          </section>
          <div class="control-toast">
            <span></span>
            <p>已添加到剪贴板</p>
          </div>
        </div>
      </div>
    </div>
  `;
}

app.innerHTML = `
  <div class="site-shell">
    ${buildHeader("home")}
    <main>
      <section class="hero-grid">
        <div class="hero-copy reveal">
          <span class="hero-badge">${homeContent.hero.label}</span>
          <h1>${homeContent.hero.title}</h1>
          <p class="hero-summary">${homeContent.hero.summary}</p>
          <div class="hero-actions">
            <a class="button button-primary" href="${homeContent.hero.primaryHref}">${homeContent.hero.primaryCta}</a>
            <a class="button button-secondary" href="${homeContent.hero.secondaryHref}">${homeContent.hero.secondaryCta}</a>
          </div>
          <div class="hero-stats" aria-label="产品概览">
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
        </div>
        <div class="reveal reveal-delay">
          ${renderProductDemo()}
        </div>
      </section>

      <section class="section-block reveal">
        <div class="section-intro">
          <span class="eyebrow">Why Chattodo</span>
          <h2>它不只是截图，也不只是待办，而是把现场问题持续推进到结论。</h2>
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

      <section class="section-block reveal" id="workflow">
        <div class="section-intro">
          <span class="eyebrow">Workflow</span>
          <h2>从截图取证到知识归档，一条完整的现场问题闭环。</h2>
        </div>
        <div class="workflow-list">
          ${homeContent.workflow
            .map(
              (item) => `
                <article class="workflow-card">
                  <span class="step-no">${item.step}</span>
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

      <section class="section-block reveal">
        <div class="section-intro">
          <span class="eyebrow">Built For</span>
          <h2>为每天处理客户问题、交付现场和内部协同的人设计。</h2>
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

      <section class="section-block reveal" id="features">
        <div class="section-intro">
          <span class="eyebrow">Core Features</span>
          <h2>围绕工单待办、排查材料和结论沉淀组织的核心能力。</h2>
        </div>
        <div class="feature-grid">
          ${homeContent.capabilities
            .map(
              (item, index) => `
                <article class="feature-card">
                  <span class="card-index">${String(index + 1).padStart(2, "0")}</span>
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
          <span class="eyebrow">Scenarios</span>
          <h2>这些场景里，Chattodo 能明显减少来回整理和重复沟通。</h2>
        </div>
        <div class="scenario-list">
          ${homeContent.scenarios.map((item) => `<p>${item}</p>`).join("")}
        </div>
      </section>

      <section class="section-block reveal" id="download">
        <div class="section-intro">
          <span class="eyebrow">Download / Docs</span>
          <h2>先按成品软件安装，再按完整用户文档建立团队使用规范。</h2>
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
          <h2>第一次接触产品时最容易问到的问题。</h2>
        </div>
        <div class="faq-preview-grid">
          ${faqItems
            .slice(0, 4)
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
