#!/usr/bin/env python3
"""platform/cert_processor.py - Phase 3: Certificate processing.
Builds certificate chains, packages PFX, validates certificates.
"""
import os, shutil, subprocess, base64
from platform.logger import get_logger, log_pass, log_fail

class CertificateProcessor:
    def __init__(self, logger=None):
        self.log = logger or get_logger()
        self.openssl = shutil.which("openssl") or "openssl"

    def build_chain(self, cert_path, intermediate_path="", root_path="", output_path=""):
        parts = [p for p in [cert_path, intermediate_path, root_path] if p and os.path.isfile(p)]
        if not output_path:
            output_path = os.path.splitext(cert_path)[0] + "-fullchain.pem"
        chain = ""
        for p in parts:
            raw = open(p,"rb").read()
            if b"BEGIN CERTIFICATE" in raw:
                chain += raw.decode(errors="ignore").strip() + "\n"
            else:
                b64 = base64.b64encode(raw).decode()
                lines = "\n".join(b64[i:i+64] for i in range(0, len(b64), 64))
                chain += f"-----BEGIN CERTIFICATE-----\n{lines}\n-----END CERTIFICATE-----\n"
        with open(output_path, "w") as f: f.write(chain)
        count = chain.count("BEGIN CERTIFICATE")
        self.log.info("Chain: %s (%d certs)", output_path, count)
        return output_path

    def build_pfx(self, cert_path, key_path, output_path="", password=""):
        if not output_path:
            output_path = os.path.splitext(cert_path)[0] + ".pfx"
        pw = f"pass:{password}"
        rc,_,e = self._run([self.openssl,"pkcs12","-export","-in",cert_path,"-inkey",key_path,"-out",output_path,"-passout",pw])
        if rc: return {"success":False,"error":f"PFX failed: {e}"}
        rc2,_,_ = self._run([self.openssl,"pkcs12","-info","-in",output_path,"-noout","-passin",pw])
        if rc2==0: log_pass(self.log,"PFX valid",output_path)
        else: log_fail(self.log,"PFX validation","check failed")
        return {"success":rc2==0,"pfx_path":output_path}

    def validate_cert(self, cert_path):
        if not os.path.isfile(cert_path): return {"valid":False,"error":f"Not found: {cert_path}"}
        rc,out,err = self._run([self.openssl,"x509","-in",cert_path,"-text","-noout"])
        return {"valid":rc==0,"details":(out if rc==0 else err)[:400]}

    def _run(self, cmd):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return r.returncode, r.stdout, r.stderr
        except Exception as e:
            return 1, "", str(e)
