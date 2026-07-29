def solution(expenses): 
    prediction = {}

    for key, value in expenses.items(): 
        prediction[key] = sum(value) // len(value)

    return prediction

def solution_weighted(expenses, months, weight):
    prediction = {}
    for key, value in expenses.items():
        old_avg = sum(value[:-months]) // len(value[:-months])
        recent_avg = sum(value[-months:]) // len(value[-months:])
        prediction[key] = old_avg * ((100 - weight) / 100) + recent_avg * (weight / 100)
    return prediction

expense_data = {
    "Office Supplies": [120, 110, 150, 130, 140],
    "Marketing": [200, 240, 220, 210, 230],
    "Utilities": [90, 95, 100, 85, 90],
    "Rent": [1000, 1000, 1000, 1000, 1000]
}

expected = {
    "Office Supplies": 135,
    "Marketing": 225,
    "Utilities": 92,
    "Rent": 1000
}

result = solution(expense_data)
weighted_result = solution_weighted(expense_data, 2, 80)
print("Result:", result)
print("Weighted Result:", weighted_result)
print("Expected:", expected)
        
