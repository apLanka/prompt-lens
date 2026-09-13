import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App";
import HomeScreen from "./screens/HomeScreen";
import SuiteEditorScreen from "./screens/SuiteEditorScreen";
import RunConfigScreen from "./screens/RunConfigScreen";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<App />}>
          <Route index element={<HomeScreen />} />
          <Route path="suites/:suiteId/edit" element={<SuiteEditorScreen />} />
          <Route path="suites/:suiteId/run" element={<RunConfigScreen />} />
          <Route path="runs/:runId" element={<HomeScreen />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
