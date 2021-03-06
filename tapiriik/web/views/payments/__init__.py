from tapiriik.settings import PP_WEBSCR, PP_RECEIVER_ID, PAYMENT_AMOUNT, PAYMENT_CURRENCY
from tapiriik.auth import Payments, User
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.shortcuts import redirect, render
import requests
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def payments_ipn(req):
    data = req.POST.dict()
    data["cmd"] = "_notify-validate"
    response = requests.post(PP_WEBSCR, data=data)
    if response.text != "VERIFIED":
        logger.error("IPN request %s not validated - response %s" % (req.POST, response.text))
        return HttpResponse(status=403)
    if req.POST["receiver_id"] != PP_RECEIVER_ID or req.POST["mc_currency"] != PAYMENT_CURRENCY:
        logger.error("IPN request %s has incorrect details" % req.POST )
        return HttpResponse(status=400)
    if req.POST["payment_status"] != "Completed":
        logger.error("IPN request %s not complete" % req.POST)
        return HttpResponse()
    logger.info("IPN request %s OK" % str(req.POST))
    payment = Payments.LogPayment(req.POST["txn_id"], amount=req.POST["mc_gross"])
    user = User.Get(req.POST["custom"])
    User.AssociatePayment(user, payment)
    return HttpResponse()


def payments_return(req):
    if req.user is None or User.HasActivePayment(req.user):
        return redirect("/")
    return render(req, "payments/return.html")


def payments_claim(req):
    err = False
    if req.user is None:
        return redirect("/")
    if "txn" in req.POST:
        if payments_claim_do(req.user, req.POST["txn"]):
            return redirect("/")
        else:
            err = True
    return render(req, "payments/claim.html", {"err": err})

def payments_claim_ajax(req):
    if req.user is None or not payments_claim_do(req.user, req.POST["txn"]):
        return HttpResponse(status=403)
    return HttpResponse()

def payments_claim_do(user, txnId):
    payment = Payments.GetPayment(txnId)
    if payment is None:
        return False
    User.AssociatePayment(user, payment)
    return True