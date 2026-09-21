# -*- coding: utf-8 -*-
"""Z38 adt_table_create · Z40 adt_ttyp_create · Z39 adt_textpool_write — süreç içi, SAHTE istemci (ağ yok).

Sahte ADT oturumu her HTTP çağrısını kaydeder; "doğru sırayla doğru uca doğru gövde gitti", "düzeltme PUT'u koştu",
"hiç ağa gidilmedi" iddiaları çağrı listesiyle kanıtlanır. Tablo testleri kütüphanenin GERÇEK
`SAPADTClient.create_table_with_ddl` metodunu sahte oturum üzerinde koşar (kilit/PUT/UNLOCK sırası kodun kendisi).
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import _helpers as H

sys.dont_write_bytecode = True
if str(H.SCRIPTS) not in sys.path:
    sys.path.insert(0, str(H.SCRIPTS))

from test_new_write_tools import TR, Oturum, SahteADT, SahteIstemci, Yanit  # noqa: E402

TR2 = "TESTK900002"
AKTIF_MD = '<adtcore:mainObject adtcore:masterLanguage="TR" adtcore:version="active"/>'


class Oturum2(Oturum):
    def __init__(self, adt):
        super().__init__(adt)
        self.headers: dict = {}

    def put(self, url, params=None, data=None, headers=None, timeout=None):
        return self.adt._kayit("PUT", url, headers, params, data)


class DdicADT(SahteADT):
    language = "TR"
    timeout_default = 30
    timeout_short = 10

    def __init__(self, yonlendir):
        super().__init__(yonlendir)
        self.session = Oturum2(self)
        self._last_lock_effective_transport = None
        from sap_adt_lib import SAPADTClient  # type: ignore
        k = SAPADTClient
        self.create_table_with_ddl = k.create_table_with_ddl.__get__(self)
        self._extract_lock_xml_field = k._extract_lock_xml_field.__get__(self)
        self._validate_object_name = k._validate_object_name.__get__(self)
        self._validate_package_name = k._validate_package_name.__get__(self)
        self.kilit_tutamaci = "HTP1"

    # textpool yolu: kütüphane kilit yardımcıları (sahte; çağrı kaydı düşer)
    def lock_object(self, object_url, access_mode="MODIFY", transport=None, **kw):
        self.cagri.append({"method": "LIB", "path": "lock_object", "params": {"url": object_url, "transport": transport},
                           "data": None, "headers": {}})
        self._last_lock_effective_transport = transport
        return self.kilit_tutamaci

    def unlock_object(self, object_url, lock_handle):
        self.cagri.append({"method": "LIB", "path": "unlock_object", "params": {"url": object_url,
                                                                                  "handle": lock_handle},
                           "data": None, "headers": {}})
        return getattr(self, "unlock_sonuc", True)


class DdicIstemci(SahteIstemci):
    def __init__(self, adt, sql=None):
        super().__init__(adt)
        self.metadata = AKTIF_MD
        self.sql = sql
        self.last_sql_error = None
        self.aktive = True   # bool ya da sırayla dönen liste (ilk aktivasyon, düzeltme sonrası ikinci)

    def activate_object(self, name, object_type=None):
        self.adt_client.cagri.append({"method": "LIB", "path": f"activate:{object_type}", "params": {"name": name},
                                      "data": None, "headers": {}})
        if isinstance(self.aktive, list):
            return self.aktive.pop(0) if self.aktive else True
        return self.aktive

    def run_sql_query(self, query, max_rows=100):
        self.adt_client.cagri.append({"method": "LIB", "path": "sql", "params": {"q": query}, "data": None,
                                      "headers": {}})
        return self.sql(query) if callable(self.sql) else self.sql


def _pass():
    from sapadt._reviewer import ReviewerResult
    return ReviewerResult(verdict="PASS")


ALANLAR = [{"name": "MANDT", "type": "mandt", "key": True},
           {"name": "BELGE", "type": "char10", "key": True},
           {"name": "ACIKLAMA", "type": "char40"}]


class DdicTextpool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(tempfile.mkdtemp(prefix="axet_ddic_"))
        cls._eski_env = {k: os.environ.get(k) for k in ("AXET_SAP_PROJECT_DIR", "ADT_SAP_TIER")}
        os.environ.pop("ADT_SAP_TIER", None)
        for k in [k for k in os.environ if k.upper().startswith("ADT_")]:
            cls._eski_env.setdefault(k, os.environ.get(k))
            os.environ.pop(k, None)
        from sapadt.tools import atom, ddic, textpool
        cls.atom, cls.ddic, cls.tp = atom, ddic, textpool
        cls._eski = (atom._get_client, ddic._varlik, ddic.run_reviewer_tablo)
        cls._sayac = 0

    @classmethod
    def tearDownClass(cls):
        cls.atom._get_client, cls.ddic._varlik, cls.ddic.run_reviewer_tablo = cls._eski
        for k, v in cls._eski_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(cls.root, ignore_errors=True)

    def setUp(self):
        type(self)._sayac += 1
        self.p = H.make_project(self.root, f"p{self._sayac}")
        os.environ["AXET_SAP_PROJECT_DIR"] = str(self.p)
        self.ddic._varlik = lambda name, t: (False, "checked_absent")
        self.ddic.run_reviewer_tablo = lambda ddl: _pass()

    def kur(self, yon, sql=None):
        adt = DdicADT(yon)
        ist = DdicIstemci(adt, sql)
        self.atom._get_client = lambda: ist
        return adt, ist

    def kaydet(self, ad, beklenen, gercek, ok):
        H.kaydet(f"DDIC {ad}", beklenen, str(gercek)[:160], ok)
        self.assertTrue(ok, f"{ad}: {gercek}")

    # ── Z38 adt_table_create ───────────────────────────────────────────────────────────────
    def _tablo_yon(self, kilit=None, canli=None, put_kod=200, unlock_kod=200):
        durum = {"ddl": None}

        def yon(c):
            m, yol, pr = c["method"], c["path"], c["params"]
            if m == "POST" and yol == "/sap/bc/adt/ddic/tables":
                return Yanit(201, "")
            if m == "POST" and pr.get("_action") == "LOCK":
                return kilit or Yanit(200, f"<DATA><LOCK_HANDLE>HT1</LOCK_HANDLE><CORRNR>{TR}</CORRNR>"
                                           "<IS_LINK_UP></IS_LINK_UP></DATA>")
            if m == "PUT":
                durum["ddl"] = c["data"]
                return Yanit(put_kod, "")
            if m == "POST" and pr.get("_action") == "UNLOCK":
                return Yanit(unlock_kod, "kilit" if unlock_kod != 200 else "")
            if m == "GET" and yol.endswith("/source/main"):
                return Yanit(200, canli if canli is not None else durum["ddl"] or "")
            return Yanit(500, "beklenmedik")
        return yon

    def test_T1_tablo_akis_sirasi(self):
        adt, _ = self.kur(self._tablo_yon(kilit=Yanit(200, "<DATA><LOCK_HANDLE>HT1</LOCK_HANDLE>"
                                                           f"<CORRNR>{TR2}</CORRNR><IS_LINK_UP></IS_LINK_UP></DATA>")))
        r = self.ddic.adt_table_create("ZAXET_T_DEN", "Deneme tablosu", ALANLAR, "ZAXET_PKG", TR)
        ag = [c for c in adt.cagri if c["method"] in ("POST", "PUT", "GET") or c["path"].startswith("activate")]
        sira = [(c["method"], c["params"].get("_action") or c["path"].rsplit("/", 1)[-1]) for c in ag]
        kabuk, put = ag[0], [c for c in ag if c["method"] == "PUT"][0]
        ok = (r.get("ok") is True
              and sira[:5] == [("POST", "tables"), ("POST", "LOCK"), ("PUT", "main"), ("POST", "UNLOCK"),
                               ("LIB", "activate:table")]
              and "define table" not in kabuk["data"] and 'adtcore:type="TABL/DT"' in kabuk["data"]
              and kabuk["headers"].get("Content-Type", "").startswith("application/vnd.sap.adt.tables.v2+xml")
              and "If-Match" not in put["headers"]
              and put["params"] == {"lockHandle": "HT1", "corrNr": TR2}
              and "key mandt : mandt not null;" in put["data"] and "#NOT_EXTENSIBLE" in put["data"]
              and r["steps"]["readback"]["ok"] is True
              and r["steps"]["create"]["effective_transport"] == TR2 and r["steps"]["create"]["warnings"])
        self.kaydet("T1 tablo: POST(DDL'siz)→LOCK→PUT(If-Match yok, CORRNR)→UNLOCK→aktive→readback",
                    "ok · sıra · CORRNR otorite", f"ok={r.get('ok')} err={r.get('error')} sıra={sira}", ok)

    def test_T2_tablo_varsayilan_kabuk_readback_fail(self):
        adt, _ = self.kur(self._tablo_yon(canli="define table zaxet_t_den {\n  key client : abap.clnt not null;\n}"))
        r = self.ddic.adt_table_create("ZAXET_T_DEN", "Deneme tablosu", ALANLAR, "ZAXET_PKG", TR)
        ok = (r.get("ok") is False and r.get("error") == "readback_mismatch"
              and r["steps"]["readback"]["reason"] == "default_shell_client_field")
        self.kaydet("T2 tablo: canlıda varsayılan client kabuğu → FAIL (aktif metadata yetmez)",
                    "readback_mismatch · default_shell", f"{r.get('error')} · {r['steps'].get('readback')}", ok)

    def test_T3_tablo_kilit_reddi_yarim_kabuk(self):
        adt, _ = self.kur(self._tablo_yon(kilit=Yanit(403, "kilitli")))
        r = self.ddic.adt_table_create("ZAXET_T_DEN", "Deneme tablosu", ALANLAR, "ZAXET_PKG", TR)
        ok = (r.get("ok") is False and r.get("error") == "partial_shell"
              and not any(c["method"] == "PUT" for c in adt.cagri)
              and not any(c["path"].startswith("activate") for c in adt.cagri))
        self.kaydet("T3 tablo: kilit 403 → partial_shell, PUT/aktivasyon YOK, silme YOK", "partial_shell",
                    f"{r.get('error')} · {[c['method'] for c in adt.cagri]}", ok)

    def test_T4_tablo_yabanci_transport(self):
        adt, _ = self.kur(self._tablo_yon(kilit=Yanit(200, "<DATA><LOCK_HANDLE>HT1</LOCK_HANDLE>"
                                                           f"<CORRNR>{TR2}</CORRNR><IS_LINK_UP>X</IS_LINK_UP></DATA>")))
        r = self.ddic.adt_table_create("ZAXET_T_DEN", "Deneme tablosu", ALANLAR, "ZAXET_PKG", TR)
        unlock = [c for c in adt.cagri if c["params"].get("_action") == "UNLOCK"]
        ok = (r.get("error") == "partial_shell" and not any(c["method"] == "PUT" for c in adt.cagri)
              and len(unlock) == 1)
        self.kaydet("T4 tablo: yabancı transport (IS_LINK_UP=X) → PUT yok, UNLOCK var", "partial_shell · unlock 1",
                    f"{r.get('error')} · unlock={len(unlock)}", ok)

    def test_T5_tablo_ag_oncesi_redler(self):
        adt, _ = self.kur(lambda c: AssertionError("ağ"))
        vakalar = [
            ("MANDT yok", self.ddic.adt_table_create("ZAXET_T_DEN", "d", ALANLAR[1:], "ZAXET_PKG", TR),
             "preflight_blocker"),
            ("ad > 16", self.ddic.adt_table_create("ZAXET_T_COK_UZUN_AD", "d", ALANLAR, "ZAXET_PKG", TR),
             "preflight_blocker"),
            ("key 'X'", self.ddic.adt_table_create("ZAXET_T_DEN", "d", ALANLAR[:2] + [{"name": "A", "type": "char1",
                                                                                          "key": "X"}],
                                                   "ZAXET_PKG", TR), "preflight_blocker"),
            ("$TMP transportsuz → Yasak C", self.ddic.adt_table_create("ZAXET_T_DEN", "d", ALANLAR, "$TMP", ""),
             "ADR_0005_C"),
            ("standart ad → Yasak A", self.ddic.adt_table_create("MARA2", "d", ALANLAR, "ZAXET_PKG", TR), "ADR_0005_A"),
        ]
        sonuc = []
        for ad, r, kod in vakalar:
            g = r.get("code") if r.get("error") == "guardrail_violation" else r.get("error")
            sonuc.append((ad, g == kod))
        ok = all(v for _a, v in sonuc) and adt.cagri == []
        self.kaydet("T5 tablo: ağ öncesi redler (MANDT/ad/anahtar/$TMP/std)", "hepsi · çağrı 0",
                    f"{sonuc} çağrı={len(adt.cagri)}", ok)

    def test_T6_tablo_reviewer_blocker(self):
        from sapadt._reviewer import ReviewerResult
        self.ddic.run_reviewer_tablo = lambda ddl: ReviewerResult(verdict="BLOCKER", blocker_count=1)
        adt, _ = self.kur(lambda c: AssertionError("ağ"))
        r = self.ddic.adt_table_create("ZAXET_T_DEN", "Deneme tablosu", ALANLAR, "ZAXET_PKG", TR)
        ok = r.get("error") == "reviewer_blocker" and adt.cagri == [] and "define table" in (r.get("ddl") or "")
        self.kaydet("T6 tablo: reviewer BLOCKER → yazma yok (denetlenen = yazılacak DDL)", "reviewer_blocker",
                    f"{r.get('error')} çağrı={len(adt.cagri)}", ok)

    # ── Z40 adt_ttyp_create ────────────────────────────────────────────────────────────────
    @staticmethod
    def _ttyp_xml(type_name="ZAXET_S_SATIR", data_type="", access="standard", kdef="standard", kind="nonUnique",
                  kk="dictionaryType", length="000010", decimals="000000"):
        tn = f"<ttyp:typeName>{type_name}</ttyp:typeName>" if type_name else "<ttyp:typeName/>"
        dt = f"<ttyp:dataType>{data_type}</ttyp:dataType>" if data_type else "<ttyp:dataType/>"
        return ('<ttyp:tableType xmlns:ttyp="http://www.sap.com/dictionary/tabletype"><ttyp:rowType>'
                f"<ttyp:typeKind>{kk}</ttyp:typeKind>{tn}<ttyp:builtInType>{dt}<ttyp:length>{length}</ttyp:length>"
                f"<ttyp:decimals>{decimals}</ttyp:decimals></ttyp:builtInType></ttyp:rowType>"
                f"<ttyp:accessType>{access}</ttyp:accessType><ttyp:primaryKey><ttyp:definition>{kdef}"
                f"</ttyp:definition><ttyp:kind>{kind}</ttyp:kind><ttyp:components/></ttyp:primaryKey></ttyp:tableType>")

    @staticmethod
    def _dd40l(rowtype="ZAXET_S_SATIR", rowkind="S", datatype="STRU", leng="000000", access="T", keydef="D",
               keykind="N", decimals="000000"):
        return {"columns": ["TYPENAME", "ROWTYPE", "ROWKIND", "DATATYPE", "LENG", "DECIMALS", "ACCESSMODE", "KEYDEF",
                            "KEYKIND"],
                "data": [["ZAXET_TT_DEN", rowtype, rowkind, datatype, leng, decimals, access, keydef, keykind]]}

    def _ttyp(self, xml_seq, sql_seq, put_kod=200, etag="etag-1", aktive=True, **kw):
        """xml_seq / sql_seq: sırayla dönen readback yanıtları (düzeltme sonrası ikinci eleman).

        xml_seq öğesi int ise o HTTP koduyla boş yanıt döner (XML kanalı ölçülemedi)."""
        sayac = {"x": 0, "s": 0}

        def yon(c):
            if c["method"] == "POST" and c["path"] == "/sap/bc/adt/ddic/tabletypes":
                return Yanit(201, "")
            if c["method"] == "GET" and c["path"] == "/sap/bc/adt/ddic/tabletypes/zaxet_tt_den":
                x = xml_seq[min(sayac["x"], len(xml_seq) - 1)]
                sayac["x"] += 1
                if isinstance(x, int):
                    return Yanit(x, "hata")
                return Yanit(200, x, {"ETag": etag} if etag else {})
            if c["method"] == "PUT":
                return Yanit(put_kod, "")
            return Yanit(500, "beklenmedik")

        def sql(q):
            s = sql_seq[min(sayac["s"], len(sql_seq) - 1)]
            sayac["s"] += 1
            return s
        adt, ist = self.kur(yon, sql)
        ist.aktive = aktive
        arg = {"row_type": "ZAXET_S_SATIR"}
        arg.update(kw)
        r = self.ddic.adt_ttyp_create("ZAXET_TT_DEN", "Deneme tablo tipi", "ZAXET_PKG", TR, **arg)
        return adt, r

    def test_Y1_ttyp_normal(self):
        adt, r = self._ttyp([self._ttyp_xml()], [self._dd40l()])
        post = [c for c in adt.cagri if c["method"] == "POST"][0]
        ok = (r.get("ok") is True and not any(c["method"] == "PUT" for c in adt.cagri)
              and post["headers"].get("Content-Type") == "application/vnd.sap.adt.tabletype.v1+xml"
              and post["params"] == {"corrNr": TR} and "<ttyp:typeName>ZAXET_S_SATIR</ttyp:typeName>" in post["data"]
              and r["steps"]["readback"]["durum"] == "dolu" and "repair" not in r["steps"])
        self.kaydet("Y1 ttyp: yarat→aktive→iki kanal dolu → OK, düzeltme YOK", "ok · PUT 0",
                    f"ok={r.get('ok')} err={r.get('error')} rb={r['steps'].get('readback', {}).get('durum')}", ok)

    def test_Y2_ttyp_satir_tipi_bos_duzeltme_kostu(self):
        adt, r = self._ttyp([self._ttyp_xml(type_name=""), self._ttyp_xml()],
                            [self._dd40l(rowtype="", rowkind="", datatype=""), self._dd40l()])
        post = [c for c in adt.cagri if c["method"] == "POST"][0]
        put = [c for c in adt.cagri if c["method"] == "PUT"]
        akt = [c for c in adt.cagri if c["path"].startswith("activate")]
        ok = (r.get("ok") is True and len(put) == 1 and put[0]["headers"].get("If-Match") == "etag-1"
              and put[0]["data"] == post["data"] and put[0]["path"] == "/sap/bc/adt/ddic/tabletypes/zaxet_tt_den"
              and len(akt) == 2 and r["steps"]["repair"]["ok"] is True
              and r["steps"]["readback"]["durum"] == "bos" and r["steps"]["readback_2"]["durum"] == "dolu")
        self.kaydet("Y2 ttyp: ROWTYPE boş → If-Match PUT (aynı XML) → yeniden aktive → dolu → OK",
                    "PUT 1 · aktive 2 · ok", f"ok={r.get('ok')} put={len(put)} akt={len(akt)} err={r.get('error')}", ok)

    def test_Y3_ttyp_duzeltme_sonrasi_hala_bos_FAIL(self):
        bos_x, bos_s = self._ttyp_xml(type_name=""), self._dd40l(rowtype="", rowkind="", datatype="")
        adt, r = self._ttyp([bos_x, bos_x], [bos_s, bos_s])
        put = [c for c in adt.cagri if c["method"] == "PUT"]
        ok = r.get("ok") is False and r.get("error") == "row_type_empty_after_repair" and len(put) == 1
        self.kaydet("Y3 ttyp: düzeltme sonrası HÂLÂ boş → FAIL (asla OK değil)", "row_type_empty_after_repair",
                    f"ok={r.get('ok')} err={r.get('error')} put={len(put)}", ok)

    def test_Y4_ttyp_kanal_celiskisi(self):
        adt, r = self._ttyp([self._ttyp_xml()], [self._dd40l(rowtype="", rowkind="", datatype="")])
        ok = (r.get("error") == "readback_channels_disagree" and not any(c["method"] == "PUT" for c in adt.cagri))
        adt2, r2 = self._ttyp([self._ttyp_xml(type_name="")], [self._dd40l()])
        ok = ok and r2.get("error") == "readback_channels_disagree"
        self.kaydet("Y4 ttyp: bir kanal dolu öbürü boş → FAIL (düzeltme yok)", "channels_disagree ×2",
                    f"{r.get('error')} · {r2.get('error')}", ok)

    def test_Y5_ttyp_sql_olculemedi(self):
        adt, r = self._ttyp([self._ttyp_xml()], [None])
        adt2, r2 = self._ttyp([self._ttyp_xml()], [{"columns": ["TYPENAME"], "data": []}])
        ok = r.get("error") == "readback_unmeasured" and r2.get("error") == "readback_unmeasured"
        self.kaydet("Y5 ttyp: DD40L okunamadı / aktif satır yok → ÖLÇÜLEMEDİ (ok:false)", "readback_unmeasured ×2",
                    f"{r.get('error')} · {r2.get('error')}", ok)

    def test_Y6_ttyp_erisim_uyumsuz(self):
        adt, r = self._ttyp([self._ttyp_xml()], [self._dd40l(access="S")])
        ok = r.get("error") == "readback_mismatch" and "ACCESSMODE" in r.get("message", "")
        self.kaydet("Y6 ttyp: DD40L erişim S ≠ standard → FAIL", "readback_mismatch", r.get("message"), ok)

    def test_Y7_ttyp_ilkel_satir(self):
        adt, r = self._ttyp([self._ttyp_xml(type_name="", data_type="CHAR", kk="predefinedAbapType")],
                            [self._dd40l(rowtype="", rowkind="", datatype="CHAR", leng="000010")],
                            row_type=None, builtin={"data_type": "CHAR", "length": 10})
        post = [c for c in adt.cagri if c["method"] == "POST"][0]
        ok = (r.get("ok") is True and "<ttyp:dataType>CHAR</ttyp:dataType>" in post["data"]
              and "predefinedAbapType" in post["data"])
        self.kaydet("Y7 ttyp: ilkel CHAR(10) satır → DATATYPE ölçüsüyle OK", "ok",
                    f"ok={r.get('ok')} err={r.get('error')} {r.get('message')}", ok)

    def test_Y8_ttyp_ag_oncesi_redler(self):
        adt, _ = self.kur(lambda c: AssertionError("ağ"))
        f = self.ddic.adt_ttyp_create
        vakalar = [
            ("ikisi birden", f("ZAXET_TT_DEN", "d", "ZAXET_PKG", TR, row_type="X", builtin={"data_type": "CHAR",
                                                                                         "length": 1})),
            ("hiçbiri", f("ZAXET_TT_DEN", "d", "ZAXET_PKG", TR)),
            ("hashed nonUnique", f("ZAXET_TT_DEN", "d", "ZAXET_PKG", TR, row_type="X", access_type="hashed",
                                   key_kind="nonUnique")),
            ("standard unique", f("ZAXET_TT_DEN", "d", "ZAXET_PKG", TR, row_type="X", key_kind="unique")),
        ]
        ok = all(r.get("error") == "preflight_blocker" for _a, r in vakalar) and adt.cagri == []
        r_tmp = f("ZAXET_TT_DEN", "d", "$TMP", "", row_type="X")
        self.kaydet("Y8 ttyp: ağ öncesi redler; $TMP transportsuz Yasak C DEĞİL (muaf)",
                    "preflight ×4 · $TMP geçer", f"{[(a, r.get('error')) for a, r in vakalar]} tmp={r_tmp.get('code')}",
                    ok and r_tmp.get("code") != "ADR_0005_C")

    # ── Z39 adt_textpool_write ─────────────────────────────────────────────────────────────
    def _tp(self, canli=None, aktif=None, put_kod=200, unlock=True, **kw):
        canli = canli or {}
        durum = {"yaz": {}}

        def yon(c):
            m, yol, pr = c["method"], c["path"], c["params"]
            if m == "GET" and "/textelements/programs/zaxet_p_den/source/" in yol:
                alt = yol.rsplit("/", 1)[-1]
                if pr.get("version") == "active":
                    return Yanit(200, (aktif or {}).get(alt, durum["yaz"].get(alt, "")))
                return Yanit(200, canli.get(alt, ""), {"ETag": f"e-{alt}"})
            if m == "PUT":
                durum["yaz"][yol.rsplit("/", 1)[-1]] = c["data"]
                return Yanit(put_kod, "DS512" if put_kod != 200 else "")
            if m == "POST" and yol == "/sap/bc/adt/activation":
                return Yanit(200, '<chkl:messages activationExecuted="true" checkExecuted="true" '
                                  'generationExecuted="true"/>')
            return Yanit(500, "beklenmedik")
        adt, ist = self.kur(yon)
        adt.unlock_sonuc = unlock
        return adt, self.tp.adt_textpool_write("ZAXET_P_DEN", TR, **kw)

    SEM = [{"key": "B01", "text": "Seçim kriterleri"}]
    SEC = [{"name": "P_BUKRS", "text": "Şirket kodu"}, {"name": "S_BELGE8", "text": "Belge"}]

    def test_P1_textpool_akis(self):
        adt, r = self._tp(symbols=self.SEM, selections=self.SEC)
        putlar = [c for c in adt.cagri if c["method"] == "PUT"]
        sira = [c["path"].rsplit("/", 1)[-1] if c["method"] != "LIB" else c["path"] for c in adt.cagri]
        i_unlock, i_px = sira.index("unlock_object"), sira.index("activation")
        sym = [c for c in putlar if c["path"].endswith("/symbols")][0]
        sel = [c for c in putlar if c["path"].endswith("/selections")][0]
        kilit = [c for c in adt.cagri if c["path"] == "lock_object"][0]
        ok = (r.get("ok") is True
              and kilit["params"] == {"url": "/sap/bc/adt/textelements/programs/zaxet_p_den", "transport": TR}
              and sym["data"] == "@MaxLength:16\r\nB01=Seçim kriterleri"
              and sel["data"] == "P_BUKRS =Şirket kodu\r\n\r\nS_BELGE8=Belge"
              and sym["params"] == {"corrNr": TR, "lockHandle": "HTP1"} and sym["headers"].get("If-Match") == "e-symbols"
              and sym["headers"].get("Content-Type") == "application/vnd.sap.adt.textelements.symbols.v1; charset=utf-8"
              and i_unlock < i_px and "activate_object" in sira
              and all(v["ok"] for v in r["steps"]["readback"].values()))
        self.kaydet("P1 textpool: GET→REPT kilit→PUT(biçim CRLF, If-Match, tutamaç)→UNLOCK→PROG/P+PX→aktif readback",
                    "ok · biçim · unlock<PX", f"ok={r.get('ok')} err={r.get('error')} sıra={sira}", ok)

    def test_P2_textpool_silinecek_giris_izinsiz(self):
        adt, r = self._tp(canli={"symbols": "@MaxLength:5\r\nB99=Eski!\r\n\r\n@MaxLength:3\r\nB01=abc"},
                          symbols=self.SEM)
        ok = (r.get("error") == "would_remove_entries" and r.get("would_remove") == {"symbols": ["B99"]}
              and not any(c["path"] == "lock_object" for c in adt.cagri))
        self.kaydet("P2 textpool: canlıdaki B99 girdide yok → izinsiz yazmaz, kilit yok", "would_remove_entries",
                    f"{r.get('error')} {r.get('would_remove')}", ok)

    def test_P3_textpool_px_terfi_etmedi(self):
        adt, r = self._tp(aktif={"selections": "P_BUKRS =?\r\n\r\nS_BELGE8=?"}, selections=self.SEC)
        ok = (r.get("ok") is False and r.get("error") == "readback_mismatch"
              and r["steps"]["readback"]["selections"]["placeholder"] == ["P_BUKRS", "S_BELGE8"])
        self.kaydet("P3 textpool: aktif sürümde `=?` → FAIL (working sürüm yanıltır)", "readback_mismatch",
                    f"{r.get('error')} {r['steps']['readback']}", ok)

    def test_P4_textpool_ag_oncesi_redler(self):
        adt, _ = self.kur(lambda c: AssertionError("ağ"))
        f = self.tp.adt_textpool_write
        vakalar = [
            ("max_length aşımı", f("ZAXET_P_DEN", TR, symbols=[{"key": "B01", "text": "uzun metin", "max_length": 4}]),
             "preflight_blocker"),
            ("sembol 4 harf", f("ZAXET_P_DEN", TR, symbols=[{"key": "B001", "text": "x"}]), "preflight_blocker"),
            ("seçim adı 9", f("ZAXET_P_DEN", TR, selections=[{"name": "P_COKUZUN", "text": "x"}]), "preflight_blocker"),
            ("boş girdi", f("ZAXET_P_DEN", TR), "preflight_blocker"),
            ("transport yok", f("ZAXET_P_DEN", "", symbols=self.SEM), "ADR_0005_C"),
            ("standart program", f("RSPARAM", TR, symbols=self.SEM), "ADR_0005_A"),
        ]
        sonuc = [(a, (r.get("code") if r.get("error") == "guardrail_violation" else r.get("error")) == k)
                 for a, r, k in vakalar]
        self.kaydet("P4 textpool: ağ öncesi redler", "hepsi · çağrı 0", f"{sonuc} çağrı={len(adt.cagri)}",
                    all(v for _a, v in sonuc) and adt.cagri == [])

    def test_P5_textpool_sahte_tutamac_ve_put_hatasi(self):
        adt = DdicADT(lambda c: Yanit(200, "", {"ETag": "e"}))
        adt.kilit_tutamaci = "NO_LOCK_SUPPORT"
        ist = DdicIstemci(adt)
        self.atom._get_client = lambda: ist
        r = self.tp.adt_textpool_write("ZAXET_P_DEN", TR, symbols=self.SEM)
        ok1 = r.get("error") == "lock_failed" and not any(c["method"] == "PUT" for c in adt.cagri)
        adt2, r2 = self._tp(put_kod=406, symbols=self.SEM)
        ok2 = (r2.get("error") == "put_failed" and any(c["path"] == "unlock_object" for c in adt2.cagri)
               and not any(c["path"] == "/sap/bc/adt/activation" for c in adt2.cagri))
        self.kaydet("P5 textpool: sahte tutamaç → yazmaz · PUT 406 → unlock var, aktivasyon yok",
                    "lock_failed · put_failed", f"{r.get('error')} · {r2.get('error')}", ok1 and ok2)


    # ── Bug-gate WARNING düzeltmeleri (2026-09-21): kapsanmayan dallar + M1-M3 · L1-L3 ─────────────
    def test_T7_tablo_put_4xx_yarim_kabuk_unlock(self):
        adt, _ = self.kur(self._tablo_yon(put_kod=400))
        r = self.ddic.adt_table_create("ZAXET_T_DEN", "Deneme tablosu", ALANLAR, "ZAXET_PKG", TR)
        unlock = [c for c in adt.cagri if c["params"].get("_action") == "UNLOCK"]
        ok = (r.get("ok") is False and r.get("error") == "partial_shell" and r["steps"]["create"].get("stage") == "put"
              and len(unlock) == 1 and unlock[0]["params"].get("lockHandle") == "HT1"
              and not any(c["path"].startswith("activate") for c in adt.cagri) and "unlock_warning" not in r)
        self.kaydet("T7 tablo: PUT 400 → partial_shell(put), UNLOCK 1, aktivasyon yok", "partial_shell · unlock 1",
                    f"{r.get('error')} stage={r['steps']['create'].get('stage')} unlock={len(unlock)}", ok)

    def test_T8_tablo_unlock_hatasi_gorunur(self):
        adt, _ = self.kur(self._tablo_yon(unlock_kod=403))
        r = self.ddic.adt_table_create("ZAXET_T_DEN", "Deneme tablosu", ALANLAR, "ZAXET_PKG", TR)
        c = r["steps"]["create"]
        ok1 = (r.get("ok") is True and c.get("unlock_ok") is False and bool(r.get("unlock_warning"))
               and any("UNLOCK" in w for w in c.get("warnings") or []))
        adt2, _ = self.kur(self._tablo_yon(put_kod=400, unlock_kod=403))
        r2 = self.ddic.adt_table_create("ZAXET_T_DEN", "Deneme tablosu", ALANLAR, "ZAXET_PKG", TR)
        ok2 = (r2.get("error") == "partial_shell" and bool(r2.get("unlock_warning"))
               and r2["steps"]["create"].get("unlock_ok") is False)
        adt3, _ = self.kur(self._tablo_yon())
        r3 = self.ddic.adt_table_create("ZAXET_T_DEN", "Deneme tablosu", ALANLAR, "ZAXET_PKG", TR)
        ok3 = r3["steps"]["create"].get("unlock_ok") is True and "unlock_warning" not in r3
        self.kaydet("T8 tablo: UNLOCK 403 → ok korunur ama unlock_ok:false + unlock_warning (başarı + PUT hatası)",
                    "uyarı görünür ×2 · 200'de uyarı yok",
                    f"ok={r.get('ok')} c={c.get('unlock_ok')} w={str(r.get('unlock_warning'))[:40]} · "
                    f"{r2.get('error')} {str(r2.get('unlock_warning'))[:30]} · {r3['steps']['create'].get('unlock_ok')}",
                    ok1 and ok2 and ok3)

    def test_T9_tablo_aktivasyon_hatasi(self):
        adt, ist = self.kur(self._tablo_yon())
        ist.aktive = False
        r = self.ddic.adt_table_create("ZAXET_T_DEN", "Deneme tablosu", ALANLAR, "ZAXET_PKG", TR)
        ok = (r.get("ok") is False and r.get("error") == "activation_failed" and "readback" not in r["steps"]
              and not any(c["method"] == "GET" for c in adt.cagri))
        self.kaydet("T9 tablo: aktivasyon False → activation_failed, readback yok", "activation_failed",
                    f"{r.get('error')} steps={sorted(r['steps'])}", ok)

    def test_T10_tablo_kucuk_harf_ad_ve_dogrulama_asamasi(self):
        adt, _ = self.kur(self._tablo_yon())
        r = self.ddic.adt_table_create("zaxet_t_den", "Deneme tablosu", ALANLAR, "ZAXET_PKG", TR)
        kabuk = [c for c in adt.cagri if c["method"] == "POST" and c["path"] == "/sap/bc/adt/ddic/tables"]
        ok1 = (r.get("ok") is True and r.get("name") == "ZAXET_T_DEN" and len(kabuk) == 1
               and 'adtcore:name="ZAXET_T_DEN"' in kabuk[0]["data"])
        adt2, _ = self.kur(self._tablo_yon())
        r2 = self.ddic.adt_table_create("ZAXET_T_DEN", "Deneme tablosu", ALANLAR, "", TR)
        msg = r2.get("message") or ""
        ok2 = (r2.get("ok") is False and r2.get("error") == "validation_error"
               and r2["steps"].get("create", {}).get("stage") == "validate" and adt2.cagri == []
               and "reddedildi" not in msg and "gidilmedi" in msg)
        self.kaydet("T10 tablo: küçük harfli ad normalize → OK · boş paket → validation_error (POST 0, doğru mesaj)",
                    "ok · validation_error", f"ok={r.get('ok')} err={r.get('error')} · {r2.get('error')} "
                    f"stage={r2['steps'].get('create', {}).get('stage')} msg={msg[:60]} "
                    f"çağrı={len(adt2.cagri)}", ok1 and ok2)

    def test_T11_tablo_csrf_istisnasi_baslik_temizlenir(self):
        adt, _ = self.kur(self._tablo_yon())

        def patla(force_refresh=False):
            raise RuntimeError("csrf ağı düştü")
        adt.fetch_csrf_token = patla
        r = self.ddic.adt_table_create("ZAXET_T_DEN", "Deneme tablosu", ALANLAR, "ZAXET_PKG", TR)
        ok = (r.get("error") == "partial_shell" and r["steps"]["create"].get("stage") == "lock"
              and "X-sap-adt-sessiontype" not in adt.session.headers
              and not any(c["params"].get("_action") == "LOCK" for c in adt.cagri))
        self.kaydet("T11 tablo: kabuk sonrası CSRF istisnası → partial_shell(lock), stateful başlık temizlendi",
                    "partial_shell · başlık yok", f"{r.get('error')} stage={r['steps']['create'].get('stage')} "
                    f"başlık={adt.session.headers}", ok)

    def test_Y9_ttyp_duzeltme_put_412(self):
        bos_x, bos_s = self._ttyp_xml(type_name=""), self._dd40l(rowtype="", rowkind="", datatype="")
        adt, r = self._ttyp([bos_x], [bos_s], put_kod=412)
        akt = [c for c in adt.cagri if c["path"].startswith("activate")]
        ok = (r.get("ok") is False and r.get("error") == "row_type_empty_repair_failed"
              and r["steps"]["repair"].get("http_status") == 412 and len(akt) == 1)
        self.kaydet("Y9 ttyp: düzeltme PUT 412 → row_type_empty_repair_failed, ikinci aktivasyon yok",
                    "repair_failed", f"ok={r.get('ok')} err={r.get('error')} akt={len(akt)}", ok)

    def test_Y10_ttyp_etag_yok(self):
        bos_x, bos_s = self._ttyp_xml(type_name=""), self._dd40l(rowtype="", rowkind="", datatype="")
        adt, r = self._ttyp([bos_x], [bos_s], etag="")
        ok = (r.get("error") == "row_type_empty_repair_failed" and r["steps"]["repair"].get("reason") == "etag_yok"
              and not any(c["method"] == "PUT" for c in adt.cagri))
        self.kaydet("Y10 ttyp: ETag yok → If-Match'siz PUT DENENMEZ", "etag_yok · PUT 0",
                    f"{r.get('error')} {r['steps'].get('repair')}", ok)

    def test_Y11_ttyp_aktivasyon_hatasi(self):
        adt, r = self._ttyp([self._ttyp_xml()], [self._dd40l()], aktive=False)
        ok = (r.get("ok") is False and r.get("error") == "activation_failed" and "readback" not in r["steps"]
              and not any(c["path"] == "sql" for c in adt.cagri))
        self.kaydet("Y11 ttyp: aktivasyon False → activation_failed, readback yok", "activation_failed",
                    f"{r.get('error')} steps={sorted(r['steps'])}", ok)

    def test_Y12_ttyp_dd40l_dolu_xml_olculemedi(self):
        adt, r = self._ttyp([500], [self._dd40l()])
        rb = r["steps"].get("readback", {})
        ok = (r.get("ok") is False and r.get("error") == "readback_unmeasured"
              and rb.get("xml_probe") == "xml_http_500" and rb.get("durum") == "olculemedi")
        self.kaydet("Y12 ttyp: DD40L dolu + XML 500 → readback_unmeasured (ölçülemedi ≠ doğru)", "readback_unmeasured",
                    f"{r.get('error')} {rb.get('xml_probe')}", ok)

    def test_Y13_ttyp_dec_ondalik_uyumsuz(self):
        dec = {"row_type": None, "builtin": {"data_type": "DEC", "length": 15, "decimals": 2}}
        x_iyi = self._ttyp_xml(type_name="", data_type="DEC", kk="predefinedAbapType", length="000015",
                               decimals="000002")
        s_iyi = self._dd40l(rowtype="", rowkind="", datatype="DEC", leng="000015", decimals="000002")
        _a, r0 = self._ttyp([x_iyi], [s_iyi], **dec)
        _a, r1 = self._ttyp([x_iyi], [self._dd40l(rowtype="", rowkind="", datatype="DEC", leng="000015",
                                                  decimals="000000")], **dec)
        _a, r2 = self._ttyp([self._ttyp_xml(type_name="", data_type="DEC", kk="predefinedAbapType", length="000015",
                                            decimals="000000")], [s_iyi], **dec)
        _a, r3 = self._ttyp([self._ttyp_xml(type_name="", data_type="DEC", kk="predefinedAbapType", length="000013",
                                            decimals="000002")], [s_iyi], **dec)
        ok = (r0.get("ok") is True
              and r1.get("error") == "readback_mismatch" and "DD40L.DECIMALS" in r1.get("message", "")
              and r2.get("error") == "readback_mismatch" and "XML decimals" in r2.get("message", "")
              and r3.get("error") == "readback_mismatch" and "XML length" in r3.get("message", ""))
        self.kaydet("Y13 ttyp: DEC 15,2 — DD40L DECIMALS=0 / XML decimals=0 / XML length=13 → readback_mismatch",
                    "ok · mismatch ×3", f"{r0.get('error')} · {str(r1.get('message'))[:70]} · "
                    f"{str(r2.get('message'))[:70]} · {str(r3.get('message'))[:70]}", ok)

    def test_Y14_ttyp_duzeltme_sonrasi_aktivasyon_hatasi(self):
        bos_x, bos_s = self._ttyp_xml(type_name=""), self._dd40l(rowtype="", rowkind="", datatype="")
        adt, r = self._ttyp([bos_x, self._ttyp_xml()], [bos_s, self._dd40l()], aktive=[True, False])
        ok = (r.get("ok") is False and r.get("error") == "activation_failed_after_repair"
              and r["steps"]["activate_2"]["ok"] is False and "readback_2" not in r["steps"])
        self.kaydet("Y14 ttyp: düzeltme PUT'u OK ama yeniden aktivasyon düştü → activation_failed_after_repair",
                    "activation_failed_after_repair", f"ok={r.get('ok')} err={r.get('error')}", ok)

    def test_P6_textpool_unlock_hatasi(self):
        adt, r = self._tp(unlock=False, symbols=self.SEM)
        ok = (r.get("ok") is True and r["steps"]["unlock"]["ok"] is False and bool(r.get("unlock_warning")))
        adt2, r2 = self._tp(unlock=False, put_kod=406, symbols=self.SEM)
        ok = ok and r2.get("error") == "put_failed" and bool(r2.get("unlock_warning"))
        self.kaydet("P6 textpool: UNLOCK başarısız → unlock_warning (başarı + PUT hatası yolunda)", "uyarı ×2",
                    f"ok={r.get('ok')} {str(r.get('unlock_warning'))[:40]} · {r2.get('error')}", ok)

    def test_P7_textpool_silme_uygulanmadi(self):
        canli = {"symbols": "@MaxLength:5\r\nB99=Eski!\r\n\r\n@MaxLength:16\r\nB01=Seçim kriterleri"}
        adt, r = self._tp(canli=canli, aktif=canli, allow_remove=True, symbols=self.SEM)
        rb = r["steps"]["readback"]["symbols"]
        ok1 = (r.get("ok") is False and r.get("error") == "readback_mismatch"
               and rb.get("remove_not_applied") == ["B99"] and rb["ok"] is False)
        adt2, r2 = self._tp(canli=canli, allow_remove=True, symbols=self.SEM)
        ok2 = r2.get("ok") is True and r2["steps"]["readback"]["symbols"].get("remove_not_applied") == []
        self.kaydet("P7 textpool: allow_remove ile silinecek B99 aktifte duruyor → readback_mismatch",
                    "remove_not_applied · temizde ok", f"{r.get('error')} {rb} · {r2.get('ok')}", ok1 and ok2)


if __name__ == "__main__":
    unittest.main()
