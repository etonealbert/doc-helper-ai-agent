data "aws_cloudfront_cache_policy" "caching_disabled" {
  name = "Managed-CachingDisabled"
}

resource "aws_cloudfront_origin_request_policy" "api" {
  name    = "doc-helper-api-origin-request"
  comment = "Forward headers required by FastAPI and CORS preflight"

  cookies_config {
    cookie_behavior = "none"
  }

  query_strings_config {
    query_string_behavior = "all"
  }

  headers_config {
    header_behavior = "whitelist"

    headers {
      items = [
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
        "Content-Type",
        "Accept",
        "Accept-Language",
        "X-Trace-Id",
      ]
    }
  }
}

resource "aws_cloudfront_distribution" "api" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = ""
  comment             = "Doc Helper API distribution"
  aliases             = ["api.albertlukmanovlabs.lol"]
  price_class         = "PriceClass_100"

  viewer_certificate {
    acm_certificate_arn      = "arn:aws:acm:us-east-1:964866958896:certificate/8ab072c7-a600-43c1-81ee-3e8f2a3a2a52"
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  origin {
    domain_name = "origin-api.albertlukmanovlabs.lol"
    origin_id   = "doc-helper-api-origin"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "doc-helper-api-origin"
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods = [
      "GET",
      "HEAD",
      "OPTIONS",
      "PUT",
      "POST",
      "PATCH",
      "DELETE",
    ]

    cached_methods = [
      "GET",
      "HEAD",
    ]

    cache_policy_id          = data.aws_cloudfront_cache_policy.caching_disabled.id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.api.id
    compress                 = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
}
