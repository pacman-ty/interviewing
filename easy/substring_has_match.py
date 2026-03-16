class Solution:
    def hasMatch(self, s: str, p: str) -> bool:

        head, tail = p.split('*')
        hlen = len(head)
        tlen = len(tail)
        start = 0
        found = False

        for i in range(len(s) - hlen + 1):
            if s[i:i + hlen] == head:
                start = i + hlen
                found = True
                break
        
        for i in range(start, len(s) - tlen + 1):
            if s[i:i + tlen] == tail:
                return found == True

        return False        
