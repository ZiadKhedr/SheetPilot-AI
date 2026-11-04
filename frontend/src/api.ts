export function token(){return sessionStorage.getItem('sheetpilot-token')||''}
export async function api<T>(path:string,method='GET',body?:unknown):Promise<T>{
 const headers:Record<string,string>={};
 if(token())headers.Authorization='Bearer '+token();
 let value:BodyInit|undefined;
 if(body instanceof FormData)value=body;
 else if(body!==undefined){headers['Content-Type']='application/json';value=JSON.stringify(body)}
 const response=await fetch('/api'+path,{method,headers,body:value});
 if(!response.ok){
  let message='Request failed ('+response.status+')';
  try{const error=await response.json();message=typeof error.detail==='string'?error.detail:JSON.stringify(error.detail)}catch{}
  throw new Error(message);
 }
 return response.json() as Promise<T>;
}
export async function download(path:string,name:string,method='GET'){
 const headers:Record<string,string>=token()?{Authorization:'Bearer '+token()}:{};
 if(method==='POST')headers['Content-Type']='application/json';
 const response=await fetch('/api'+path,{method,headers,body:method==='POST'?'{}':undefined});
 if(!response.ok){const data=await response.json();throw new Error(data.detail||'Download failed')}
 const blob=await response.blob();const url=URL.createObjectURL(blob);
 const anchor=document.createElement('a');anchor.href=url;anchor.download=name;anchor.click();
 setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export async function downloadBackup(){
 const archive=await api<{name:string;content:string}>('/backups/export?encoding=base64');
 const decoded=atob(archive.content),bytes=new Uint8Array(decoded.length);
 for(let i=0;i<decoded.length;i++)bytes[i]=decoded.charCodeAt(i);
 const url=URL.createObjectURL(new Blob([bytes],{type:'application/zip'}));
 const anchor=document.createElement('a');anchor.href=url;anchor.download='SheetPilot-Backup.zip';anchor.click();
 setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export function formatMoney(amount:string|number,currency='USD',precision=2){
 if(!/^[A-Z]{3}$/.test(currency))return String(amount)+' (currency needs review)';
 return new Intl.NumberFormat('en-US',{style:'currency',currency,maximumFractionDigits:precision}).format(Number(amount));
}
export function label(value:string){return value.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase())}
