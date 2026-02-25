desired_amount = 1200
fee_rate = 0.12
withdraw_amount = desired_amount / (1 - fee_rate)
print(round(withdraw_amount, 2))