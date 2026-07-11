# 7. Max Repeated Characters

**Difficulty:** 🟢 Easy
**Source:** Unpublished / company interview problem (not indexed on LeetCode)

---

## Problem

Given a string `text`, find the maximum length of consecutive identical characters (excluding whitespace) and return all characters that occur consecutively with this maximum length, in the order they appear in the string.

Example 1:

```
Input: text = "thiis iss a teest seentennce"
Output: ['i', 's', 'e', 'e', 'n']
Explanation:
Consecutive sequences: "ii" (length 2), "ss" (length 2), "ee" (length 2), "nn" (length 2)
```

Example 2:

```
Input: text = "hello"
Output: ['l']
Explanation:
Consecutive sequences: "h" (length 1), "e" (length 1), "ll" (length 2), "o" (length 1)
"ll" is the longest run, so only 'l' is returned.
```

**Constraints:**

- `0 <= text.length <= 10^5`
- `text` consists of lowercase English letters and whitespaces.
- The result should preserve the order of appearance in the original string.

---

## Solution

See [solution.py](./solution.py)

Single pass over the string tracking the current run's character and length. Whitespace breaks a run without being added as a candidate. Whenever a new run exceeds the current max, the result list is reset; ties append to it. O(n) time, O(k) auxiliary space where k is the number of max-length runs.
