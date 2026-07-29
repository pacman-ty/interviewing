from itertools import combinations

def solution(history): 
    pair_frequency = {}

    for lst in history:
        lst = sorted(lst)
        for i, j in combinations(lst, 2): 
            if (i, j) in pair_frequency:
                pair_frequency[i, j] += 1
            else:
                pair_frequency[i, j] = 1

    frequency_list = []

    for k in pair_frequency:
        i, j = k
        frequency_list.append([i, j, pair_frequency[k]])
    
    
    frequency_list.sort(key=lambda x: x[2], reverse=True)
    
    return frequency_list


transaction_histories = [
    ["Payroll Services", "Accounting Software"],
    ["Tax Software", "Accounting Software"],
    ["Payroll Services", "Tax Software"],
    ["Payroll Services", "Accounting Software", "Tax Software"]
]

print(solution(transaction_histories))
