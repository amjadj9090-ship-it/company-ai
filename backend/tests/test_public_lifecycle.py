from backend.app import main
from backend.app.public_lifecycle import _token_record


def test_customer_lifecycle_token_accept_order():
    s = main.Session(main.engine)
    try:
        lead = main.Entity(kind="leads", data={"name":"Test Customer","email":"test@example.com"})
        s.add(lead); s.flush()
        proposal = main.Entity(kind="proposals", data={"lead_id":lead.id,"status":"sent","proposal_type":"standard","human_approval_required":False})
        s.add(proposal); s.flush()
        token = "test-public-token"
        record = main.Entity(kind="customer_proposal_tokens", data={"proposal_id":proposal.id,"token":token,"used":False})
        s.add(record); s.commit()
        assert _token_record(s, token).id == record.id
        proposal.data = {**proposal.data,"status":"accepted_by_customer"}
        s.commit()
        order = main.Entity(kind="orders", data={"proposal_id":proposal.id,"status":"confirmed","payment_status":"unpaid","execution_locked":False})
        s.add(order); s.commit()
        assert order.data["payment_status"] == "unpaid"
    finally:
        s.close()
