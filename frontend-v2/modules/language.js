const FALLBACK="en";
const SUPPORTED=new Set(["ar","en","es","fr","de","pt","it","tr","nl"]);
export function detectLanguage(){const list=Array.isArray(navigator.languages)?navigator.languages:[navigator.language];for(const value of list){const code=String(value||"").toLowerCase().split("-")[0];if(SUPPORTED.has(code))return code}return FALLBACK}
export function setDocumentLanguage(code){document.documentElement.lang=code;document.documentElement.dir=code==="ar"?"rtl":"ltr"}
