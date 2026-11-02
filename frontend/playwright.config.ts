import { defineConfig } from '@playwright/test';
const python=process.env.SHEETPILOT_PYTHON||(process.platform==='win32'?'../.venv/Scripts/python.exe':'../.venv/bin/python');
export default defineConfig({
 testDir:'./e2e',timeout:240000,expect:{timeout:20000},workers:1,
 use:{baseURL:'http://127.0.0.1:8010',channel:process.env.PLAYWRIGHT_CHANNEL||undefined,headless:true,viewport:{width:1440,height:1040},trace:'retain-on-failure'},
 reporter:[['list'],['html',{open:'never'}]],
 webServer:{command:python+' -m uvicorn sheetpilot.api:app --host 127.0.0.1 --port 8010',
  url:'http://127.0.0.1:8010/api/health',reuseExistingServer:false,timeout:30000,
  env:{SHEETPILOT_DATA_DIR:'.data/e2e',SHEETPILOT_ACCESS_TOKEN:'',SHEETPILOT_READ_TOKEN:''}},
});
