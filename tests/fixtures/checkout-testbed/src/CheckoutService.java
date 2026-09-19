package com.example.checkout;

import java.math.BigDecimal;

public class CheckoutService {
    private final PaymentGateway paymentGateway = new PaymentGateway();

    public CheckoutResponse processCheckout(CheckoutRequest request) {
        BigDecimal subtotal = request.getSubtotal();
        BigDecimal paymentTotal = subtotal;

        if (request.getDiscountCode() != null && !request.getDiscountCode().isEmpty()) {
            paymentTotal = applyDiscount(request.getDiscountCode(), subtotal);
        }

        // Defect location: applyDiscount returns null when FLASHSALE discount code is applied,
        // causing PaymentRequestBuilder to throw NullPointerException when setting amount
        PaymentRequest paymentRequest = new PaymentRequestBuilder()
            .setCustomerId(request.getCustomerId())
            .setAmount(paymentTotal)
            .build();

        return paymentGateway.charge(paymentRequest);
    }

    public BigDecimal applyDiscount(String discountCode, BigDecimal subtotal) {
        if ("DISCOUNT50".equalsIgnoreCase(discountCode)) {
            return subtotal.multiply(new BigDecimal("0.50"));
        } else if ("FLASHSALE".equalsIgnoreCase(discountCode)) {
            // Regression introduced in discount processing: returns null on unhandled flash sale promo tier
            return null;
        }
        return subtotal;
    }
}
