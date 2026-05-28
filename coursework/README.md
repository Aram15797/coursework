# PTMS — Կուրսային աշխատանք / Coursework

Այս թղթապանակում գտնվում է «**Տվյալների հենքերի նախագծում**» առարկայի
կուրսային աշխատանքի հաշվեբացատրագիրը՝ PTMS (Project & Task Management
System) նախագծի շուրջ։

## Բովանդակություն

```
coursework/
├── PTMS_kursayin_ashkhatank.pdf   # Վերջնական PDF
├── fonts/
│   └── sylfaen.ttf                # Հայերեն + Լատինական տառատեսակ
├── src/
│   ├── content.py                 # Ամբողջ տեքստային բովանդակություն
│   └── build_pdf.py               # ReportLab-ի օգնությամբ PDF գեներացիա
└── full_text.txt                  # Բնագիր PDF-ի տեքստային հղում
```

## Հավաքել PDF-ը

```bash
cd coursework
pip install reportlab
python3 src/build_pdf.py
```

Արդյունքում կստեղծվի `PTMS_kursayin_ashkhatank.pdf` ֆայլը։

## Տեխնիկական մանրամասներ

* Տառատեսակ՝ **Sylfaen** (Latin + Armenian + Cyrillic + Georgian coverage)
* Էջի չափս՝ Letter (612 × 792 pt), 1-inch լուսանցքներ
* Հիմնական տեքստ՝ 12 pt, վերնագրեր՝ 14 pt, գլխավոր վերնագիր՝ 24 pt
* TOC-ը գեներացվում է երկու անցումով (dry-run → real render)
* «Bold» էֆեկտը ստեղծվում է text render mode 2-ով (fill + stroke),
  քանի որ Sylfaen-ը bold տարբերակ չունի
