# proDrop

Automated dropshipping for ERPNext, built as a Frappe app.

Part of the EzDevSoft stack: it sits next to the PROXC brand app (`proxc`), ProAds (ads) and EzTrack (delivery tracking).

## Status

Early scaffold. Working today: `prodrop/trends.py` (product scoring, with tests). Stubs, not yet wired: the CJ supplier connector, the Sales Order hook and the scheduled jobs.

## Planned loop

1. Trend radar scores candidate products (demand, margin, competition).
2. Approved products become ERPNext Items with supplier price and stock rules.
3. ProAds launches small paused test campaigns; winners scale, losers stop.
4. A submitted Sales Order triggers the supplier order.
5. EzTrack tracking and delivery status flow back to the order.

## Install

```bash
bench get-app https://github.com/amsshk/proDrop.git
bench --site your-site install-app prodrop
```

Requires ERPNext on Frappe v16.

## Tests

The scoring module needs no bench:

```bash
python -m unittest discover -s tests -t .
```

## License

MIT
