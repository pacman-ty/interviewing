class Solution:
    def maxVowels(self, s: str, k: int) -> int:
        vowels = {'a', 'e', 'i', 'o', 'u'}

        vowel_count = 0
        max_vowels = 0 

        for c in s[:k]:
            if c in vowels: 
                max_vowels += 1
                vowel_count += 1
        
        for i in range(len(s) - k): 
            vowel_count = vowel_count - self.is_vowel(s[i], vowels) + self.is_vowel(s[i + k], vowels)
            if vowel_count > max_vowels:
                max_vowels = vowel_count
        
        return max_vowels
    
    def is_vowel(self, c, vowels):
        if c in vowels:
            return 1
        else: 
            return 0 


