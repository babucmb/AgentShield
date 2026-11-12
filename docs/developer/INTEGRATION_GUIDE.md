# AgentShield developer integration guide

Base URL: `http://localhost:8000`

## Register and authenticate

```powershell
$body = @{ email = "developer@example.com"; password = "strong-password"; organization_name = "Demo Workspace" } | ConvertTo-Json
$registration = Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/auth/register -ContentType application/json -Body $body
$token = $registration.access_token
```

Create an organization API key:

```powershell
$headers = @{ Authorization = "Bearer $token" }
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/orgs/api-keys -Headers $headers -ContentType application/json -Body '{"label":"shopping-agent"}'
```

## Configure policy

```powershell
$policy = '{"max_transaction_amount":3000,"daily_spending_limit":10000,"monthly_spending_limit":50000,"allowed_merchants":[],"blocked_merchants":[],"allowed_currencies":["INR"],"restricted_categories":[],"max_quantity":5,"requires_human_approval":true,"active":true}'
Invoke-RestMethod -Method Put -Uri http://localhost:8000/api/policy -Headers $headers -ContentType application/json -Body $policy
```

## Submit and evaluate a proposal

```powershell
$proposal = Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/proposals -Headers @{"Idempotency-Key"="demo-001"} -ContentType application/json -Body '{"instruction":"Find a Bluetooth keyboard under ₹3,000. Ask me before checkout.","product_id":"keyboard-001"}'
$decision = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/proposals/$($proposal.id)/evaluate"
```

Continue with `POST /api/proposals/{id}/approval`, `POST /api/approvals/{id}` with `{"approve":true}`, then the PayPal order and capture endpoints. Amounts are calculated from the server catalogue; the client cannot choose the payment amount.
