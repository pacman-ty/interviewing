def solution(s1, s2, s3)
    diff = []
    
    for i in range(len(s1)):
        if s1[i] == s2[i]:
            if s2[i] == s3[i]: 
                diff.append(0)
            else: 
                diff.append(1)
        elif s1[i] != s2[i]: 
            if s2[i] == s3[i]:
                diff.append(1)
            elif s1[i] == s3[i]:
                diff.append(1)
            else: 
                diff.append(2)
        else:
            diff.append(0)

        if sum(diff) > 

    if sum(diff) > 3:
        return "Ambiguous"
    elif sum(diff) < 3: k

