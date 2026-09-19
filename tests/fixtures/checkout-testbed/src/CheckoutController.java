package com.example.checkout;

public class CheckoutController {
    private final CheckoutService checkoutService = new CheckoutService();

    public CheckoutResponse handleCheckout(CheckoutRequest request) {
        return checkoutService.processCheckout(request);
    }
}
