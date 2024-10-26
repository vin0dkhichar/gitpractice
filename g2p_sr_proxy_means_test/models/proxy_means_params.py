from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SRProxyMeanTestParams(models.Model):
    _name = "sr.proxy.means.test.params"
    _description = "Proxy Means Test Params"
    _rec_name = "pmt_name"

    pmt_name = fields.Char(
        string="PMT Name",
    )
    target = fields.Selection(
        [("individual", "Individual"), ("group", "Group")],
        string="Target",
    )
    kind = fields.Many2one(
        "g2p.group.kind",
        string="Kind",
    )

    pmt_line_ids = fields.One2many("sr.proxy.means.test.line", "pmt_id", string="Proxy Means Test Lines")

    target_name = fields.Boolean(default=True)

    @api.onchange("target")
    def _onchange_target(self):
        if self.target == "group":
            self.write({"target_name": False})
        else:
            self.write({"target_name": True})

    @api.constrains("target", "kind")
    def _check_unique_pmt(self):
        for rec in self:
            existing_pmt = self.search_count(
                [("target", "=", rec.target), ("kind", "=", rec.kind.id), ("id", "!=", rec.id)]
            )
            if existing_pmt > 0:
                raise ValidationError("A Proxy Means Test for this kind and target already exists.")

    @api.model
    def create(self, vals):
        if "target" in vals and "kind" in vals:
            existing_pmt = self.search_count([("target", "=", vals["target"]), ("kind", "=", vals["kind"])])
            if existing_pmt > 0:
                raise ValidationError("A Proxy Means Test for this kind and target already exists.")
        rec = super().create(vals)
        rec.compute_related_partners_pmt_score()
        return rec

    def write(self, vals):
        for rec in self:
            if "target" in vals and vals["target"] != rec.target:
                existing_pmt = self.search_count(
                    [("target", "=", vals["target"]), ("kind", "=", rec.kind.id), ("id", "!=", rec.id)]
                )
                if existing_pmt > 0:
                    raise ValidationError("A Proxy Means Test for this kind and target already exists.")
            if "kind" in vals and vals["kind"] != rec.kind.id:
                existing_pmt = self.search_count(
                    [("target", "=", rec.target), ("kind", "=", vals["kind"]), ("id", "!=", rec.id)]
                )
                if existing_pmt > 0:
                    raise ValidationError("A Proxy Means Test for this kind and target already exists.")
        rec = super().write(vals)
        for record in self:
            record.compute_related_partners_pmt_score()
        return rec

    def unlink(self):
        for rec in self:
            partners = self.env["res.partner"].search([("kind", "=", rec.kind.id)])
            for partner in partners:
                partner.pmt_score = 0

        return super().unlink()

    def compute_related_partners_pmt_score(self):
        partners = self.env["res.partner"].search([("kind", "=", self.kind.id)])
        for partner in partners:
            partner._compute_pmt_score()


class SRProxyMeanTestLine(models.Model):
    _name = "sr.proxy.means.test.line"
    _description = "Proxy Means Test Line"

    pmt_id = fields.Many2one("sr.proxy.means.test.params", string="Proxy Means Test")
    pmt_field = fields.Selection(selection="get_fields_label", string="Field")
    pmt_weightage = fields.Float(string="Weightage")

    def get_fields_label(self):
        reg_info = self.env["res.partner"]
        ir_model_obj = self.env["ir.model.fields"]
        excluded_fields = {
            "pmt_score",
            "message_needaction_counter",
            "message_has_error_counter",
            "message_attachment_count",
            "message_bounce",
            "active_lang_count",
            "partner_latitude",
            "partner_longitude",
            "color",
            "id",
            "meeting_count",
            "employees_count",
            "partner_gid",
            "certifications_count",
            "certifications_company_count",
            "event_count",
            "payment_token_count",
            "days_sales_outstanding",
            "journal_item_count",
            "bank_account_count",
            "supplier_rank",
            "customer_rank",
            "duplicated_bank_account_partners_count",
            "task_count",
            "z_ind_grp_num_individuals",
            "program_membership_count",
            "entitlements_count",
            "cycles_count",
            "inkind_entitlements_count",
            "credit_limit",
        }

        choice = []
        for field in reg_info._fields.items():
            ir_model_field = ir_model_obj.search([("model", "=", "res.partner"), ("name", "=", field[0])])
            field_type = ir_model_field.ttype
            if field_type in ["integer", "float"] and field[0] not in excluded_fields:
                choice.append((field[0], field[0]))
        return choice

    def write(self, vals):
        res = super().write(vals)

        for line in self:
            line.pmt_id.compute_related_partners_pmt_score()
        return res
