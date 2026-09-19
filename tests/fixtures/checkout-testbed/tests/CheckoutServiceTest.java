package com.example.checkout;

import org.junit.jupiter.api.Test;
import java.math.BigDecimal;
import static org.junit.jupiter.api.Assertions.*;

public class CheckoutServiceTest {
    @Test
    public void testProcessCheckoutWithFlashSaleDiscount() {
        CheckoutService service = new CheckoutService();
        CheckoutRequest request = new CheckoutRequest("cust_123", new BigDecimal("100.00"), "FLASHSALE");
        // Fails with NullPointerException: paymentTotal cannot be null for payment processing
        CheckoutResponse response = service.processCheckout(request);
        assertNotNull(response);
        assertEquals("SUCCESS", response.getStatus());
    }
}
