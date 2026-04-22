import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: 4173,
  },
  preview: {
    host: "0.0.0.0",
    port: 4173,
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        docs_index: resolve(__dirname, "docs/index.html"),
        docs_getting_started: resolve(__dirname, "docs/getting-started.html"),
        docs_installation: resolve(__dirname, "docs/installation.html"),
        docs_configuration: resolve(__dirname, "docs/configuration.html"),
        docs_features: resolve(__dirname, "docs/features.html"),
        docs_faq: resolve(__dirname, "docs/faq.html"),
      },
    },
  },
});
