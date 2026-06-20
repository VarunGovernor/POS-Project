# CounterOS Demo Walkthrough

## Prepare

```sh
scripts/dev/reset-demo-db.sh --yes
scripts/dev/start-demo.sh
```

Open `http://127.0.0.1:3000/startup`.

## Flow

1. Start backend.
2. Start frontend.
3. Open startup screen.
4. Login with `cashier` / `cashier123`.
5. Open cashier session.
6. Create patient.
7. View catalog.
8. Create draft bill.
9. Add service.
10. Edit quantity.
11. Finalize cash bill.
12. View bill detail.
13. View receipt.
14. Print receipt using development printer.
15. Reprint receipt with reason.
16. View sync screen.
17. Run manual sync retry using development adapter.
18. View recovery screen.
19. Run recovery scan.
20. View reports.
21. Update editable setting.
22. Create support bundle.
23. View audit logs.
24. Close cashier session.

## Notes

Printing uses the development printer adapter. Sync uses the development sync
adapter. Both are implemented foundations, not production integrations.
