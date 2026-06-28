import os, threading, uuid
from decimal import Decimal
os.environ["SECRET_KEY"]="verification_secret_key_0123456789_abcdef"
os.environ["DATABASE_URL"]="postgresql://arcade_user:arcade_password@localhost:5433/arcade_management"
os.environ["ENVIRONMENT"]="development"; os.environ["DEBUG"]="false"
from app.database import SessionLocal
from app.models.card import Card, Transaction, CardStatus, CardType

cuid="RACE"+uuid.uuid4().hex[:6].upper()
db=SessionLocal()
db.add(Card(card_uid=cuid, owner="Race", card_type=CardType.REGULAR, status=CardStatus.ACTIVE, balance=Decimal("100.00")))
db.commit(); db.close()

results=[]; lock=threading.Lock(); start=threading.Barrier(20)
def worker(i):
    start.wait()
    db=SessionLocal(); r="?"
    try:
        card=db.query(Card).filter(Card.card_uid==cuid).with_for_update().first()  # same lock the endpoint uses
        if card.balance < Decimal("10"):
            db.rollback(); r="INSUFFICIENT"
        else:
            card.balance=card.balance-Decimal("10")
            db.add(Transaction(card_uid=cuid, amount=Decimal("10"), transaction_type="DEDUCT", notes="race"))
            db.commit(); r="OK"
    except Exception as e:
        db.rollback(); r="ERR:"+type(e).__name__
    finally:
        db.close()
    with lock: results.append(r)

ts=[threading.Thread(target=worker,args=(i,)) for i in range(20)]
[t.start() for t in ts]; [t.join() for t in ts]
ok=results.count("OK")
db=SessionLocal(); final=db.query(Card).filter(Card.card_uid==cuid).first().balance; db.close()
print("results:", sorted(results))
print("OK=%d  final_balance=%s  (100 - 10*OK = %s)" % (ok, final, Decimal('100')-Decimal(10)*ok))
print("H3 CONCURRENCY RESULT:", "FAIL - OVERDRAFT" if (float(final)<0 or ok>10) else "PASS - no overdraft, row locking holds")
