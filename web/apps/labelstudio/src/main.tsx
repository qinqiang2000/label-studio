import { registerAnalytics } from "@humansignal/core";
registerAnalytics();

// 动态设置 favicon
import logoUrl from "./assets/images/logo.png";

// 设置动态 favicon
const setFavicon = (url: string) => {
  const link = (document.querySelector("link[rel*='icon']") as HTMLLinkElement) || document.createElement("link");
  link.type = "image/png";
  link.rel = "shortcut icon";
  link.href = url;
  document.getElementsByTagName("head")[0].appendChild(link);
};

setFavicon(logoUrl);

import "./app/App";
import "./utils/service-worker";
