package com.example.checkout;

import java.math.BigDecimal;

public class PaymentRequestBuilder {
    private String customerId;
    private BigDecimal amount;

    public PaymentRequestBuilder setCustomerId(String customerId) {
        this.customerId = customerId;
        return this;
    }

    public PaymentRequestBuilder setAmount(BigDecimal amount) {
        if (amount == null) {
            throw new NullPointerException("paymentTotal cannot be null for payment processing");
        }
        this.amount = amount;
        return this;
    }

    public PaymentRequest build() {
        return new PaymentRequest(customerId, amount);
    }
}
