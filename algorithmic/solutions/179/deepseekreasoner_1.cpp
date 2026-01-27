#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cassert>

using namespace std;

// Compare two non-negative integer strings
// Return -1 if a<b, 0 if a==b, 1 if a>b
int cmp(const string& a, const string& b) {
    if (a.size() != b.size()) return a.size() < b.size() ? -1 : 1;
    if (a < b) return -1;
    if (a > b) return 1;
    return 0;
}

// Add two non-negative integer strings
string add(const string& a, const string& b) {
    int i = a.size()-1, j = b.size()-1, carry = 0;
    string res;
    while (i >= 0 || j >= 0 || carry) {
        int d1 = i >= 0 ? a[i--] - '0' : 0;
        int d2 = j >= 0 ? b[j--] - '0' : 0;
        int sum = d1 + d2 + carry;
        res.push_back('0' + (sum % 10));
        carry = sum / 10;
    }
    reverse(res.begin(), res.end());
    return res;
}

// Subtract b from a, assuming a >= b
string sub(const string& a, const string& b) {
    int i = a.size()-1, j = b.size()-1, borrow = 0;
    string res;
    while (i >= 0) {
        int d1 = (a[i--] - '0') - borrow;
        int d2 = j >= 0 ? b[j--] - '0' : 0;
        if (d1 < d2) {
            d1 += 10;
            borrow = 1;
        } else {
            borrow = 0;
        }
        res.push_back('0' + (d1 - d2));
    }
    // Remove trailing zeros (which become leading zeros after reversal)
    while (res.size() > 1 && res.back() == '0') res.pop_back();
    reverse(res.begin(), res.end());
    return res;
}

// Absolute difference |a-b|
string abs_diff(const string& a, const string& b) {
    if (cmp(a, b) >= 0) {
        return sub(a, b);
    } else {
        return sub(b, a);
    }
}

// Normalize integer string: remove leading zeros, but keep "0"
string normalize(string s) {
    size_t pos = s.find_first_not_of('0');
    if (pos == string::npos) return "0";
    return s.substr(pos);
}

struct Candidate {
    string sum;
    vector<int> taken;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    string W;
    cin >> n >> W;
    W = normalize(W);
    
    vector<pair<string, int>> nums;
    string total = "0";
    for (int i = 0; i < n; ++i) {
        string s;
        cin >> s;
        s = normalize(s);
        nums.emplace_back(s, i);
        total = add(total, s);
    }
    
    // If total sum <= W, take all
    if (cmp(total, W) <= 0) {
        for (int i = 0; i < n; ++i) {
            cout << 1 << (i == n-1 ? '\n' : ' ');
        }
        return 0;
    }
    
    // Sort numbers in descending order
    sort(nums.begin(), nums.end(), [](const pair<string,int>& a, const pair<string,int>& b) {
        return cmp(a.first, b.first) > 0;
    });
    
    // Heuristics
    vector<Candidate> candidates;
    
    // 1. Greedy build descending
    {
        vector<int> taken(n, 0);
        string S = "0";
        for (const auto& p : nums) {
            string sum = add(S, p.first);
            if (cmp(sum, W) <= 0) {
                taken[p.second] = 1;
                S = sum;
            }
        }
        candidates.push_back({S, taken});
    }
    
    // 2. Greedy build ascending (process in reverse order)
    {
        vector<int> taken(n, 0);
        string S = "0";
        for (auto it = nums.rbegin(); it != nums.rend(); ++it) {
            const auto& p = *it;
            string sum = add(S, p.first);
            if (cmp(sum, W) <= 0) {
                taken[p.second] = 1;
                S = sum;
            }
        }
        candidates.push_back({S, taken});
    }
    
    // 3. Greedy removal descending
    {
        vector<int> taken(n, 1);
        string S = total;
        for (const auto& p : nums) {
            string newS = sub(S, p.first);
            if (cmp(newS, W) >= 0) {
                taken[p.second] = 0;
                S = newS;
            }
        }
        candidates.push_back({S, taken});
    }
    
    // 4. Greedy removal ascending (process in reverse order)
    {
        vector<int> taken(n, 1);
        string S = total;
        for (auto it = nums.rbegin(); it != nums.rend(); ++it) {
            const auto& p = *it;
            string newS = sub(S, p.first);
            if (cmp(newS, W) >= 0) {
                taken[p.second] = 0;
                S = newS;
            }
        }
        candidates.push_back({S, taken});
    }
    
    // Choose the candidate with smallest |W - S|
    int best_idx = 0;
    string best_diff = abs_diff(W, candidates[0].sum);
    for (int i = 1; i < 4; ++i) {
        string diff = abs_diff(W, candidates[i].sum);
        if (cmp(diff, best_diff) < 0) {
            best_diff = diff;
            best_idx = i;
        }
    }
    
    // Output
    const vector<int>& ans = candidates[best_idx].taken;
    for (int i = 0; i < n; ++i) {
        cout << ans[i] << (i == n-1 ? '\n' : ' ');
    }
    
    return 0;
}