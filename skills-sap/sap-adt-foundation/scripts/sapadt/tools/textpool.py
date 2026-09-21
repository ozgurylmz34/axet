# -*- coding: utf-8 -*-
"""adt_textpool_write (Z39, aXet 2026-09-21) — klasik program metin havuzu: metin sembolleri + seçim metinleri.

Neden ayrı araç: `adt_push_source` yalnız `source/main`'i taşır; metin öğeleri ayrı uçta, ayrı kilitle yaşar.
Yüklenmezse `TEXT-xxx` ve seçim ekranı etiketleri çalışma anında BOŞ görünür (program aktif ve sözdizimi temiz
olsa bile).

Akış (kaynak çekirdek `playbook/adt-programs.md` §23.7 "6 zorunlu cephe" + `scripts/push_textpool.py`):
  ön kontrol (ağsız) → her alt kaynak için GET (ETag + canlı içerik; silinecek giriş varsa izin şart)
  → KİLİT metin öğeleri kaynağında (`/textelements/programs/<prog>`, REPT — program kilidi DEĞİL; transport ile)
  → etkin transport kilit yanıtından → her alt kaynağa PUT (If-Match + lockHandle + corrNr; `_get_headers` +
  `_request_with_csrf_retry` = CSRF + stateful) → gerçek kilit tutamacı ŞART → UNLOCK (finally, aktivasyondan
  ÖNCE: aksi hâlde PROG/PX aktivasyonu aracın kendi kilidine çarpar) → PROG/P aktivasyonu → AÇIK PROG/PX
  aktivasyonu (program zaten aktifse PROG/P no-op olur ve metin havuzunu terfi ettirmez) → `?version=active`
  readback: her beklenen giriş aktif sürümde aynı metinle var mı (`=?` yer tutucu = FAIL).
"""
from __future__ import annotations

from typing import Any

from sapadt._app import profil_tool
from sapadt._conn import get_active_tier
from sapadt.guardrails import (
    GuardrailViolation,
    require_customer_namespace,
    require_transport,
    require_writable_tier,
)

_KOK = "/sap/bc/adt/textelements/programs/"
_SAHTE_TUTAMAC = ("NO_LOCK_SUPPORT", "IMPLICIT_LOCK", None, "")


def _get_client():
    from sapadt.tools.atom import _get_client as _g
    return _g()


def _err_from_exc(exc: Exception) -> dict:
    from sapadt.tools.atom import _err_from_exc as _e
    return _e(exc)


def _capture():
    from sapadt.tools.composite import _capture as _c
    return _c()


def _px_govdesi(prog_l: str, prog_u: str) -> str:
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">'
            f'<adtcore:objectReference adtcore:uri="{_KOK}{prog_l}"'
            f' adtcore:type="PROG/PX" adtcore:name="{prog_u}"/>'
            '</adtcore:objectReferences>')


# Profil: reçete kaynak çekirdekte yalnız s4_private sistemde canlı ölçüldü (kanıtsız genişletme yok).
@profil_tool(available_on=("s4_private",))
def adt_textpool_write(
    name: str,
    transport: str,
    symbols: list[dict] | None = None,
    selections: list[dict] | None = None,
    allow_remove: bool = False,
) -> dict:
    """Write a classic program's text pool (text symbols + selection texts), activate PROG/P + PROG/PX, verify active.

    Args:
        name: Z/Y program adı.
        transport: Değiştirilebilir İSTEK numarası (zorunlu; kilit yanıtındaki CORRNR otoritedir).
        symbols: Metin sembolleri — [{"key": "B01", "text": "Seçim kriterleri", "max_length"?: 30}].
            `key` tam 3 harf/rakam (kodda `TEXT-b01`). `max_length` verilmezse metnin uzunluğu; metin onu aşarsa
            ağa gitmeden BLOCKER (SAP DS512).
        selections: Seçim metinleri — [{"name": "P_BUKRS", "text": "Şirket kodu"}]; ad en çok 8 karakter.
            DDIC'ten türeyen etiket kullanılmaz; verilen metin yazılır.
        allow_remove: Alt kaynak PUT ile BÜTÜNÜYLE değişir. Canlıda olup girdide olmayan giriş SİLİNECEKSE
            varsayılan `false` → `would_remove_entries` (hiçbir şey yazılmaz). Silmeyi kullanıcı onayladıysa `true`.
            Mevcut girişleri korumak için onları da girdiye ekle.
        Başlıklar (headings) desteklenmez: yazım biçimi kaynakta belgelenmedi.

    Returns:
        {ok, name, type:'prog', written:[alt], steps:{pre_flight, read, lock, put, unlock, activate_prog,
         activate_px, readback}, effective_transport, error?, message?}
    """
    try:
        require_writable_tier(get_active_tier(), what="text pool write")
        require_customer_namespace(name, what="program", object_type="prog")
        require_transport(transport, what="text pool write")
    except GuardrailViolation as gv:
        return gv.as_dict()
    from utils import textpool as tp  # type: ignore
    steps: dict[str, Any] = {}
    on = tp.on_kontrol(symbols, selections)
    steps["pre_flight"] = on
    temel = {"name": name.upper(), "type": "prog", "steps": steps}
    if on["verdict"] == "BLOCKER":
        return {"ok": False, "error": "preflight_blocker", **temel,
                "message": "Metin havuzu ön kontrolü BLOCKER (SAP'ye gidilmedi): "
                           + "; ".join(f["message"] for f in on["findings"])}
    alt_girdi = [(a, g) for a, g in (("symbols", symbols), ("selections", selections)) if g]
    yuk = {a: (tp.sembol_yuku(g) if a == "symbols" else tp.secim_yuku(g)) for a, g in alt_girdi}
    temel["written"] = [a for a, _ in alt_girdi]

    try:
        client = _get_client()
    except Exception as exc:  # noqa: BLE001
        return {**_err_from_exc(exc), **temel}
    adt = getattr(client, "adt_client", None) or client
    prog_l, prog_u = name.lower(), name.upper()
    kok = adt.url.rstrip("/") + _KOK + prog_l
    te_url = _KOK + prog_l

    # 1) Canlı oku: ETag + silinecek giriş kontrolü (yazmadan ÖNCE).
    etag: dict[str, str] = {}
    steps["read"] = {}
    for alt, g in alt_girdi:
        try:
            r = adt._request_with_csrf_retry("get", f"{kok}/source/{alt}",
                                             headers=adt._get_headers(accept_type=tp.ALT_KAYNAK_CT[alt]), timeout=30)
        except Exception as exc:  # noqa: BLE001
            steps["read"][alt] = {"ok": False, "reason": f"exception:{type(exc).__name__}"}
            return {"ok": False, "error": "read_failed", **temel,
                    "message": f"{alt} canlı okunamadı — silinecek giriş kontrolü yapılamadı, yazma denenmedi."}
        kod = int(getattr(r, "status_code", 0) or 0)
        if kod == 404:
            steps["read"][alt] = {"ok": False, "http_status": 404}
            return {"ok": False, "error": "not_found", **temel,
                    "message": f"{prog_u} metin öğeleri ucu 404 — program yok ya da henüz yaratılmadı."}
        if kod != 200:
            steps["read"][alt] = {"ok": False, "http_status": kod, "body_head": str(getattr(r, "text", ""))[:300]}
            return {"ok": False, "error": "read_failed", **temel,
                    "message": f"{alt} canlı okuma HTTP {kod} — yazma denenmedi."}
        etag[alt] = (getattr(r, "headers", {}) or {}).get("ETag", "")
        sil = tp.silinecekler(alt, r.text or "", g)
        steps["read"][alt] = {"ok": True, "etag_present": bool(etag[alt]), "would_remove": sil}
    silinecek = {a: v["would_remove"] for a, v in steps["read"].items() if v.get("would_remove")}
    if silinecek and not allow_remove:
        return {"ok": False, "error": "would_remove_entries", **temel, "would_remove": silinecek,
                "message": ("PUT alt kaynağı BÜTÜNÜYLE değiştirir; canlıdaki şu girişler silinecekti: "
                            + "; ".join(f"{a}: {', '.join(v)}" for a, v in silinecek.items())
                            + ". Korumak için girdiye ekle; silmek kullanıcı onaylıysa allow_remove=true. Yazılmadı.")}

    # 2) Kilit — metin öğeleri (REPT) kaynağında.
    try:
        with _capture() as buf:
            tutamac = adt.lock_object(te_url, access_mode="MODIFY", transport=transport)
        steps["lock"] = {"ok": tutamac not in _SAHTE_TUTAMAC, "log": buf.getvalue().strip()[:400]}
    except Exception as exc:  # noqa: BLE001
        steps["lock"] = {"ok": False, **_err_from_exc(exc)}
        return {"ok": False, "error": "lock_failed", **temel,
                "message": "Metin öğeleri kilidi alınamadı — hiçbir şey yazılmadı. Kilit silinmez (Kesin Yasak C); "
                           "sahibini kullanıcıya bildir."}
    if tutamac in _SAHTE_TUTAMAC:
        return {"ok": False, "error": "lock_failed", **temel,
                "message": f"Gerçek kilit tutamacı alınamadı ({tutamac}) — metin öğeleri PUT'u tutamaç ister; "
                           "yazılmadı."}
    etkin = getattr(adt, "_last_lock_effective_transport", None) or transport
    temel["effective_transport"] = etkin
    if etkin != transport:
        steps["lock"]["transport_note"] = f"SAP farklı transport bildirdi: istenen={transport} → etkin={etkin}"

    # 3) PUT her alt kaynak; UNLOCK finally (aktivasyondan ÖNCE).
    steps["put"] = {}
    put_hatasi = None
    try:
        for alt, _g in alt_girdi:
            h = adt._get_headers(accept_type=tp.ALT_KAYNAK_CT[alt],
                                 content_type=tp.ALT_KAYNAK_CT[alt] + "; charset=utf-8")
            if etag.get(alt):
                h["If-Match"] = etag[alt]
            r = adt._request_with_csrf_retry("put", f"{kok}/source/{alt}", headers=h,
                                             params={"corrNr": etkin, "lockHandle": tutamac},
                                             data=yuk[alt].encode("utf-8"), timeout=60)
            kod = int(getattr(r, "status_code", 0) or 0)
            steps["put"][alt] = {"ok": kod in (200, 201, 204), "http_status": kod}
            if kod not in (200, 201, 204):
                steps["put"][alt]["body_head"] = str(getattr(r, "text", ""))[:600]
                put_hatasi = alt
                break
    except Exception as exc:  # noqa: BLE001
        put_hatasi = put_hatasi or "exception"
        steps["put"]["exception"] = _err_from_exc(exc)
    finally:
        try:
            with _capture():
                acildi = adt.unlock_object(te_url, tutamac)
            steps["unlock"] = {"ok": bool(acildi)}
        except Exception as exc:  # noqa: BLE001
            steps["unlock"] = {"ok": False, "reason": f"exception:{type(exc).__name__}"}
    kilit_uyari = None if steps["unlock"]["ok"] else (
        "Kilit AÇILAMADI — sonraki yazımlar kilit hatası alabilir. Kilit silinmez (Kesin Yasak C); kullanıcıya bildir.")
    if put_hatasi:
        out = {"ok": False, "error": "put_failed", **temel,
               "message": f"{put_hatasi} PUT'u başarısız — aktivasyon denenmedi. steps.put'a bak "
                          "(406 DS512 = biçim/uzunluk; 423 = kilit/transport)."}
        if kilit_uyari:
            out["unlock_warning"] = kilit_uyari
        return out

    # 4) Aktivasyon: PROG/P, ardından AÇIK PROG/PX.
    try:
        with _capture():
            akt = adt.activate_object(prog_u, f"/sap/bc/adt/programs/programs/{prog_l}")
        steps["activate_prog"] = {"ok": bool((akt or {}).get("success")),
                                  "errors": [e.get("message") for e in (akt or {}).get("errors", [])][:10]}
    except Exception as exc:  # noqa: BLE001
        steps["activate_prog"] = {"ok": False, **_err_from_exc(exc)}
    try:
        from sap_adt_lib import aktivasyon_govde_hukmu  # type: ignore
        ph = adt._get_headers(accept_type="application/vnd.sap.adt.objectactivation.result.v1+xml",
                              content_type="application/xml")
        pr = adt._request_with_csrf_retry("post", adt.url.rstrip("/") + "/sap/bc/adt/activation", headers=ph,
                                          data=_px_govdesi(prog_l, prog_u).encode("utf-8"),
                                          params={"method": "activate", "preauditRequested": "true"}, timeout=60)
        hk = aktivasyon_govde_hukmu(getattr(pr, "text", ""))
        steps["activate_px"] = {"http_status": int(getattr(pr, "status_code", 0) or 0), "body_verdict": hk["hukum"],
                                "reason": hk["sebep"], "note": "Nihai hüküm aktif sürüm readback'indedir."}
    except Exception as exc:  # noqa: BLE001
        steps["activate_px"] = {"ok": False, **_err_from_exc(exc)}

    # 5) Readback — ?version=active (working sürüm PUT'lanan metni gösterip yanıltır).
    steps["readback"] = {}
    tamam = True
    for alt, g in alt_girdi:
        try:
            r = adt._request_with_csrf_retry("get", f"{kok}/source/{alt}",
                                             headers=adt._get_headers(accept_type=tp.ALT_KAYNAK_CT[alt]),
                                             params={"version": "active"}, timeout=30)
            kod = int(getattr(r, "status_code", 0) or 0)
        except Exception as exc:  # noqa: BLE001
            steps["readback"][alt] = {"ok": False, "reason": f"exception:{type(exc).__name__}"}
            tamam = False
            continue
        if kod != 200:
            steps["readback"][alt] = {"ok": False, "http_status": kod}
            tamam = False
            continue
        steps["readback"][alt] = tp.readback_karsilastir(alt, r.text or "", g,
                                                         silinecek=steps["read"][alt].get("would_remove"))
        tamam = tamam and steps["readback"][alt]["ok"]
    out = {"ok": tamam, **temel}
    if kilit_uyari:
        out["unlock_warning"] = kilit_uyari
    if not tamam:
        out["error"] = "readback_mismatch"
        out["message"] = ("Metinler yazıldı ama AKTİF sürümde doğrulanamadı (eksik / farklı / `=?` / silinmesi onaylanan "
                          "giriş hâlâ duruyor: steps.readback.*.remove_not_applied) — metin havuzu "
                          "terfi etmemiş olabilir; ekranda metin görünmez. steps.activate_px ve steps.readback'e bak.")
    return out
