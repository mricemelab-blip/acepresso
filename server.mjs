// Independent, read-only web server for ACEpresso original files.
// This file exists on a preview-only branch; source pages are unchanged.
import http from 'node:http';
import {readFile, stat} from 'node:fs/promises';
import {resolve, join, sep, extname} from 'node:path';
const root = resolve(process.cwd());
const port = Number(process.env.PORT || 3000);
const types={'.html':'text/html; charset=utf-8','.htm':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.gif':'image/gif','.ico':'image/x-icon','.pdf':'application/pdf','.woff':'font/woff','.woff2':'font/woff2','.ttf':'font/ttf','.xml':'application/xml; charset=utf-8','.txt':'text/plain; charset=utf-8'};
http.createServer(async(req,res)=>{
  try{
    if(!['GET','HEAD'].includes(req.method)){res.writeHead(405,{'Allow':'GET, HEAD'}).end();return}
    let path=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    if(path==='/'||path.endsWith('/'))path+='index.html';
    if(path.includes('\\')||path.includes('\\0')){res.writeHead(400).end('Invalid path');return}
    const file=resolve(root,'.'+path);
    if(file!==root&&!file.startsWith(root+sep)){res.writeHead(403).end('Forbidden');return}
    const info=await stat(file);
    if(!info.isFile()){res.writeHead(404).end('Not found');return}
    const mime=types[extname(file).toLowerCase()]||'application/octet-stream';
    const headers={'Content-Type':mime,'Content-Length':info.size,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'};
    if(req.method==='HEAD'){res.writeHead(200,headers).end();return}
    const data=await readFile(file);res.writeHead(200,headers).end(data);
  }catch(e){const status=e.code==='ENOENT'?404:e.code==='EACCES'?403:400;res.writeHead(status,{'Content-Type':'text/plain; charset=utf-8'}).end(status===404?'File not found':'Request failed')}
}).listen(port,'0.0.0.0',()=>console.log('ACEpresso original review serving on',port));
