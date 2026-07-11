"""
7. Max Repeated Characters
Difficulty: Easy
Source: Unpublished / company interview problem (not indexed on LeetCode)
"""

class MaxConsecutiveChars:
    def find_max_consecutive(self, text):
        """
        Find the maximum length of consecutive identical characters (excluding
        whitespace) and return all characters that occur consecutively with
        this maximum length, in order of appearance.

        Time Complexity: O(n)
        - Single pass through the string
        - The inner while loop only advances i, so total iterations across
          both loops is bounded by n

        Space Complexity: O(k)
        - k = number of characters tied for the max run length
        - No auxiliary data structures beyond the result list

        Best case: O(1) when a single run is strictly longest (k = 1)
        Worst case: O(n) when every run has the same length, e.g. "ababab"
        (every character ties for the max, so k grows to n)
        """
        if not text:
            return []

        max_length = 0
        result = []
        i = 0
        while i < len(text):
            char = text[i]

            # Whitespace breaks a run and is never a candidate itself
            if char.isspace():
                i += 1
                continue

            # Extend the run while the next character matches
            length = 1
            while i + 1 < len(text) and text[i + 1] == char:
                length += 1
                i += 1

            # New max: reset result. Tie: append to result.
            if length > max_length:
                max_length = length
                result = [char]
            elif length == max_length:
                result.append(char)

            i += 1

        return result
