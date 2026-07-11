resource "aws_dynamodb_table" "crm_records" {
  name         = "doc-helper-records"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "record_id"

  attribute {
    name = "record_id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  lifecycle {
    prevent_destroy = true
  }
}
