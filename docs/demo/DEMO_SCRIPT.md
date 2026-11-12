# AgentShield hackathon demo script

## Opening (20 seconds)

“AI can recommend a purchase, but it should not be allowed to move money by itself. AgentShield is an authorization firewall between the agent and PayPal.”

## Live flow (about 2 minutes)

1. Open `http://localhost:5174`.
2. Enter: `Find a Bluetooth keyboard under ₹3,000. Ask me before checkout.`
3. Select **Bluetooth Wireless Keyboard — ₹2,500**.
4. Click **Evaluate proposal**.
5. Explain the structured intent and the deterministic rules: category, Bluetooth feature, budget, currency, quantity, and approval.
6. Click **Approve exact proposal**.
7. Create the PayPal Sandbox order and open the returned approval URL.
8. Approve with the PayPal Sandbox personal buyer account.
9. Capture from AgentShield and show the payment status and audit event.

## Safety proof (about 40 seconds)

1. Select **Wired USB Keyboard — ₹2,200** for the Bluetooth request; show `BLOCK` because the required feature fails.
2. Select **Premium Bluetooth Keyboard — ₹3,500**; show `BLOCK` because the budget fails.
3. Explain that changing the product or amount changes the proposal fingerprint, so the old approval cannot authorize it.

## Closing

“PayPal supplies the payment infrastructure. AgentShield supplies the AI purchase authorization, policy enforcement, explicit approval, and audit trail before payment execution.”

Do not claim a live payment, AI provider call, or webhook delivery unless it was completed during the recorded session.
