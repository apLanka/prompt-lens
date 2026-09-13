import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App";
import HomeScreen from "./screens/HomeScreen";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<App />}>
          <Route index element={<HomeScreen />} />
          <Route path="suites/:suiteId/edit" element={<HomeScreen />} />
          <Route path="suites/:suiteId/run" element={<HomeScreen />} />
          <Route path="runs/:runId" element={<HomeScreen />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
