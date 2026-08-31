import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
// During `npm run dev`, proxy /api to the Express backend on :4000.
export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            "/api": { target: "http://localhost:4000", changeOrigin: true },
        },
    },
    build: { outDir: "dist", sourcemap: false },
});
