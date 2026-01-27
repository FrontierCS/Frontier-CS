#include <bits/stdc++.h>
using namespace std;

static inline int charIndex(unsigned char c) {
    if (c >= '0' && c <= '9') return c - '0';
    return 10 + (c - 'A');
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) s2.clear();
    if (!s1.empty() && s1.back() == '\r') s1.pop_back();
    if (!s2.empty() && s2.back() == '\r') s2.pop_back();

    const int ALPH = 36;
    int n = (int)s1.size();
    int m = (int)s2.size();

    // Count frequencies to reserve
    vector<int> cnt1(ALPH, 0), cnt2(ALPH, 0);
    for (unsigned char c : s1) cnt1[charIndex(c)]++;
    for (unsigned char c : s2) cnt2[charIndex(c)]++;

    // Build position lists
    vector<vector<int>> pos1(ALPH), pos2(ALPH);
    for (int k = 0; k < ALPH; ++k) {
        if (cnt1[k]) pos1[k].reserve(cnt1[k]);
        if (cnt2[k]) pos2[k].reserve(cnt2[k]);
    }
    for (int i = 0; i < n; ++i) pos1[charIndex((unsigned char)s1[i])].push_back(i);
    for (int j = 0; j < m; ++j) pos2[charIndex((unsigned char)s2[j])].push_back(j);

    // Pointers for next occurrence queries
    vector<int> ptr1(ALPH, 0), ptr2(ALPH, 0);

    auto nextPos1 = [&](int ci, int at) -> int {
        auto &v = pos1[ci];
        int &p = ptr1[ci];
        while (p < (int)v.size() && v[p] < at) ++p;
        if (p < (int)v.size()) return v[p];
        return INT_MAX;
    };
    auto nextPos2 = [&](int ci, int at) -> int {
        auto &v = pos2[ci];
        int &p = ptr2[ci];
        while (p < (int)v.size() && v[p] < at) ++p;
        if (p < (int)v.size()) return v[p];
        return INT_MAX;
    };

    string res;
    res.reserve((size_t)n + (size_t)m);

    // Trim common prefix
    int pref = 0;
    while (pref < n && pref < m && s1[pref] == s2[pref]) ++pref;
    if (pref > 0) res.append(pref, 'M');

    // Trim common suffix (after prefix)
    int i = pref, j = pref;
    int i_end = n, j_end = m;
    int tail = 0;
    while (i_end > i && j_end > j && s1[i_end - 1] == s2[j_end - 1]) {
        ++tail;
        --i_end;
        --j_end;
    }

    // Greedy alignment in the middle region [i, i_end) and [j, j_end)
    const int baseW = 64;
    const int largeW = 8192;
    const int thr = 32;
    int mismatchStreak = 0;

    while (i < i_end && j < j_end) {
        // Extend run of matches
        int ii = i, jj = j;
        while (ii < i_end && jj < j_end && s1[ii] == s2[jj]) { ++ii; ++jj; }
        int run = ii - i;
        if (run > 0) {
            res.append(run, 'M');
            i = ii; j = jj;
            mismatchStreak = 0;
            if (i >= i_end || j >= j_end) break;
        }

        // Mismatch handling
        int c1 = charIndex((unsigned char)s1[i]);
        int c2 = charIndex((unsigned char)s2[j]);

        int p2 = nextPos2(c1, j + 1);
        if (p2 >= j_end || p2 - j > baseW) p2 = INT_MAX;

        int p1 = nextPos1(c2, i + 1);
        if (p1 >= i_end || p1 - i > baseW) p1 = INT_MAX;

        if (p1 == INT_MAX && p2 == INT_MAX) {
            ++mismatchStreak;
            if (mismatchStreak >= thr) {
                int p2x = nextPos2(c1, j + 1);
                if (p2x >= j_end || p2x - j > largeW) p2x = INT_MAX;
                int p1x = nextPos1(c2, i + 1);
                if (p1x >= i_end || p1x - i > largeW) p1x = INT_MAX;

                if (p2x != INT_MAX || p1x != INT_MAX) {
                    if (p2x != INT_MAX && (p1x == INT_MAX || (p2x - j) <= (p1x - i))) {
                        int cnt = p2x - j;
                        res.append(cnt, 'I');
                        j = p2x;
                        mismatchStreak = 0;
                        continue;
                    } else {
                        int cnt = p1x - i;
                        res.append(cnt, 'D');
                        i = p1x;
                        mismatchStreak = 0;
                        continue;
                    }
                }
            }
            // Fallback to substitution
            res.push_back('M');
            ++i; ++j;
        } else if (p2 != INT_MAX && (p1 == INT_MAX || (p2 - j) <= (p1 - i))) {
            int cnt = p2 - j;
            res.append(cnt, 'I');
            j = p2;
            mismatchStreak = 0;
        } else {
            int cnt = p1 - i;
            res.append(cnt, 'D');
            i = p1;
            mismatchStreak = 0;
        }
    }

    // Remaining in middle segments
    if (i < i_end) {
        res.append(i_end - i, 'D');
        i = i_end;
    }
    if (j < j_end) {
        res.append(j_end - j, 'I');
        j = j_end;
    }

    // Append common suffix matches
    if (tail > 0) res.append(tail, 'M');

    // Output
    fwrite(res.data(), 1, res.size(), stdout);
    return 0;
}