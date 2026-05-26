# Showcase

## Muc Tieu Demo

Chung minh he thong co the chay het chu trinh marketing nha khoa ma khong can API key:

1. Crawler Agent tao insight doi thu tu fixture.
2. Content Agent tao ban nhap Facebook post.
3. Manager Agent kiem tra compliance va duyet.
4. Publisher Agent dry-run payload an toan.

## Lenh Chay

```bash
python main.py
python -m tests.smoke_workflow
python web_app.py
```

## Output Mau

```txt
=== BAO CAO NGAY ===
Tong quan insight doi thu: da phan tich 3 nguon...

=== CHIEN LUOC ===
Thong diep chu dao: Tu van nha khoa ca nhan hoa...

=== BAI DANG DUYET ===
Nu cuoi tu tin bat dau tu buoi tu van dung cach
...

=== PUBLISH RESULT ===
{'publisher_status': 'dry_run', ...}
```

## Giao Dien Web

Truy cap:

```txt
http://127.0.0.1:8765
```

Nut "Chay workflow" goi backend that va render lai bao cao, chien luoc, bai dang duyet, publish dry-run.

## Trang Thai Hoan Thanh

- Da co source code chay duoc.
- Da co fallback khi thieu dependency/API key.
- Da co smoke test toi thieu.
- Da co README sach hon de nguoi tiep theo khong bi lech ky vong.
