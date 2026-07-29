def solution(n, pairs, k, code): 
    pairs_list = pairs.split(",")

    code_map = {}

    for p in pairs_list: 
        p1, p2 = p.split()
        
        if len(p1) > len(p2):
            code_map[p1] = p2
            code_map[p2] = p2
        else: 
            code_map[p1] = p1
            code_map[p2] = p1

    final_code = ""
    code_list = code.split(",")

    for index, c in enumerate(code_list): 
        final_code += code_map[c]

        if index + 1 != k:
            final_code = final_code + ","

    return final_code

print(solution(3, "joll fdskjfd,euzf un,abcd efgh", 5, "abcd,joll,joll,euzf,fdskjfd"))

