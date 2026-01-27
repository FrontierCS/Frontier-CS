#include <iostream>
#include <string>
#include <algorithm>

using namespace std;

void greedy_subsequence(const string &a, const string &b, string &res) {
    res.clear();
    res.reserve(min(a.size(), b.size()));
    size_t j = 0, m = b.size();
    for (size_t i = 0, n = a.size(); i < n && j < m; ++i) {
        char c = a[i];
        while (j < m && b[j] != c) ++j;
        if (j < m) {
            res.push_back(c);
            ++j;
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) s2.clear();

    if (!s1.empty() && s1.back() == '\r') s1.pop_back();
    if (!s2.empty() && s2.back() == '\r') s2.pop_back();

    string best, cand;

    // Forward: S1 vs S2
    greedy_subsequence(s1, s2, cand);
    best.swap(cand);

    // Forward: S2 vs S1
    greedy_subsequence(s2, s1, cand);
    if (cand.size() > best.size()) best.swap(cand);

    // Reverse both strings
    reverse(s1.begin(), s1.end());
    reverse(s2.begin(), s2.end());

    // Reversed: S1^R vs S2^R
    greedy_subsequence(s1, s2, cand);
    if (cand.size() > best.size()) {
        reverse(cand.begin(), cand.end());
        best.swap(cand);
    }

    // Reversed: S2^R vs S1^R
    greedy_subsequence(s2, s1, cand);
    if (cand.size() > best.size()) {
        reverse(cand.begin(), cand.end());
        best.swap(cand);
    }

    cout << best << '\n';
    return 0;
}