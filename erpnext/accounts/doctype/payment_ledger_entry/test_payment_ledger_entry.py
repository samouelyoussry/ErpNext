# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe import qb
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.party import get_party_account
from erpnext.stock.doctype.item.test_item import create_item


# class TestPaymentLedgerEntry(FrappeTestCase):
class TestPaymentLedgerEntry(unittest.TestCase):
	def setUp(self):
		self.create_company()
		self.create_item()
		self.create_customer()
		self.clear_old_entries()

	# def tearDown(self):
	# 	frappe.db.rollback()

	def create_company(self):
		company_name = "_Test Payment Ledger"
		company = None
		if frappe.db.exists("Company", company_name):
			company = frappe.get_doc("Company", company_name)
		else:
			company = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": company_name,
					"country": "India",
					"default_currency": "INR",
					"create_chart_of_accounts_based_on": "Standard Template",
					"chart_of_accounts": "Standard",
				}
			)
			company = company.save()

		self.company = company.name
		self.cost_center = company.cost_center
		self.warehouse = "All Warehouses - _PL"
		self.income_account = "Sales - _PL"
		self.expense_account = "Cost of Goods Sold - _PL"
		self.debit_to = "Debtors - _PL"
		self.creditors = "Creditors - _PL"

		# create bank account
		if frappe.db.exists("Account", "HDFC - _PL"):
			self.bank = "HDFC - _PL"
		else:
			bank_acc = frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "HDFC",
					"parent_account": "Bank Accounts - _PL",
					"company": self.company,
				}
			)
			bank_acc.save()
			self.bank = bank_acc.name

	def create_item(self):
		item_name = "_Test PL Item"
		item = create_item(
			item_code=item_name, is_stock_item=0, company=self.company, warehouse=self.warehouse
		)
		self.item = item if isinstance(item, str) else item.item_code

	def create_customer(self):
		name = "_Test PL Customer"
		if frappe.db.exists("Customer", name):
			self.customer = name
		else:
			customer = frappe.new_doc("Customer")
			customer.customer_name = name
			customer.type = "Individual"
			customer.save()
			self.customer = customer.name

	def create_sales_invoice(
		self, qty=1, rate=100, posting_date=nowdate(), do_not_save=False, do_not_submit=False
	):
		"""
		Helper function to populate default values in sales invoice
		"""
		sinv = create_sales_invoice(
			qty=qty,
			rate=rate,
			company=self.company,
			customer=self.customer,
			item_code=self.item,
			item_name=self.item,
			cost_center=self.cost_center,
			warehouse=self.warehouse,
			debit_to=self.debit_to,
			parent_cost_center=self.cost_center,
			update_stock=0,
			currency="INR",
			is_pos=0,
			is_return=0,
			return_against=None,
			income_account=self.income_account,
			expense_account=self.expense_account,
			do_not_save=do_not_save,
			do_not_submit=do_not_submit,
		)
		return sinv

	def create_payment_entry(self, amount=100, posting_date=nowdate()):
		"""
		Helper function to populate default values in payment entry
		"""
		payment = create_payment_entry(
			company=self.company,
			payment_type="Receive",
			party_type="Customer",
			party=self.customer,
			paid_from=self.debit_to,
			paid_to=self.bank,
			paid_amount=amount,
		)
		payment.posting_date = posting_date
		return payment

	def clear_old_entries(self):
		doctype_list = [
			"GL Entry",
			"Payment Ledger Entry",
			"Sales Invoice",
			"Purchase Invoice",
			"Payment Entry",
			"Journal Entry",
		]
		for doctype in doctype_list:
			qb.from_(qb.DocType(doctype)).delete().where(qb.DocType(doctype).company == self.company).run()

	def create_journal_entry(
		self, acc1=None, acc2=None, amount=0, posting_date=None, cost_center=None
	):
		je = frappe.new_doc("Journal Entry")
		je.posting_date = posting_date or nowdate()
		je.company = self.company
		je.user_remark = "test"
		if not cost_center:
			cost_center = self.cost_center
		je.set(
			"accounts",
			[
				{
					"account": acc1,
					"cost_center": cost_center,
					"debit_in_account_currency": amount if amount > 0 else 0,
					"credit_in_account_currency": abs(amount) if amount < 0 else 0,
				},
				{
					"account": acc2,
					"cost_center": cost_center,
					"credit_in_account_currency": amount if amount > 0 else 0,
					"debit_in_account_currency": abs(amount) if amount < 0 else 0,
				},
			],
		)
		return je

	def test_create_all_types(self):
		transaction_date = nowdate()
		amount = 100
		# full payment using PE
		si1 = self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)
		pe2 = get_payment_entry(si1.doctype, si1.name).save().submit()

		# partial payment of invoice using PE
		si2 = self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)
		pe2 = get_payment_entry(si2.doctype, si2.name)
		pe2.get("references")[0].allocated_amount = 50
		pe2.get("references")[0].outstanding_amount = 50
		pe2 = pe2.save().submit()

		# reconcile against return invoice
		si3 = self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)
		cr_note1 = self.create_sales_invoice(
			qty=-1, rate=amount, posting_date=transaction_date, do_not_save=True, do_not_submit=True
		)
		cr_note1.is_return = 1
		cr_note1.return_against = si3.name
		cr_note1 = cr_note1.save().submit()

		# reconcile against return invoice using JE
		si4 = self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)
		cr_note2 = self.create_sales_invoice(
			qty=-1, rate=amount, posting_date=transaction_date, do_not_save=True, do_not_submit=True
		)
		cr_note2.is_return = 1
		cr_note2 = cr_note2.save().submit()
		je1 = self.create_journal_entry(
			self.debit_to, self.debit_to, amount, posting_date=transaction_date
		)
		je1.get("accounts")[0].party_type = je1.get("accounts")[1].party_type = "Customer"
		je1.get("accounts")[0].party = je1.get("accounts")[1].party = self.customer
		je1.get("accounts")[0].reference_type = cr_note2.doctype
		je1.get("accounts")[0].reference_name = cr_note2.name
		je1.get("accounts")[1].reference_type = si4.doctype
		je1.get("accounts")[1].reference_name = si4.name
		je1 = je1.save().submit()

	def test_dummy(self):
		pass
