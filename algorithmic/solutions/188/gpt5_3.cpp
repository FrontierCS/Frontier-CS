#include <bits/stdc++.h>
using namespace std;

static inline int charIndex(unsigned char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= '0' && c <= '9') return 26 + (c - '0');
    return -1;
}

static inline int nextPos(const vector<int>& v, int& ptr, int target) {
    int sz = (int)v.size();
    while (ptr < sz && v[ptr] < target) ++ptr;
    if (ptr < sz) return v[ptr];
    return INT_MAX;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) s1.clear();
    if (!getline(cin, s2)) s2.clear();
    if (!s1.empty() && s1.back() == '\r') s1.pop_back();
    if (!s2.empty() && s2.back() == '\r') s2.pop_back();

    const int ALPH = 36;

    // Count frequencies
    array<int, ALPH> cnt1{}, cnt2{};
    for (unsigned char c : s1) {
        int id = charIndex(c);
        if (id >= 0) ++cnt1[id];
    }
    for (unsigned char c : s2) {
        int id = charIndex(c);
        if (id >= 0) ++cnt2[id];
    }

    // Build position arrays with reserve
    vector<vector<int>> pos1(ALPH), pos2(ALPH);
    for (int i = 0; i < ALPH; ++i) {
        if (cnt1[i] > 0) pos1[i].reserve(cnt1[i]);
        if (cnt2[i] > 0) pos2[i].reserve(cnt2[i]);
    }
    for (int i = 0; i < (int)s1.size(); ++i) {
        int id = charIndex((unsigned char)s1[i]);
        if (id >= 0) pos1[id].push_back(i);
    }
    for (int j = 0; j < (int)s2.size(); ++j) {
        int id = charIndex((unsigned char)s2[j]);
        if (id >= 0) pos2[id].push_back(j);
    }

    // Greedy two-pointer with lookahead using next occurrence lists
    string res;
    res.reserve(min(s1.size(), s2.size()));
    array<int, ALPH> ptr1{}, ptr2{};
    int i = 0, j = 0, n = (int)s1.size(), m = (int)s2.size();
    while (i < n && j < m) {
        unsigned char a = (unsigned char)s1[i];
        unsigned char b = (unsigned char)s2[j];
        if (a == b) {
            res.push_back((char)a);
            ++i; ++j;
        } else {
            int ia = charIndex(a);
            int ib = charIndex(b);
            if (ia < 0 && ib < 0) { ++i; ++j; continue; }
            if (ia < 0) { // skip s1[i]
                ++i;
                continue;
            }
            if (ib < 0) { // skip s2[j]
                ++j;
                continue;
            }
            int nj = nextPos(pos2[ia], ptr2[ia], j); // next in s2 for s1[i]
            int ni = nextPos(pos1[ib], ptr1[ib], i); // next in s1 for s2[j]
            if (nj == INT_MAX && ni == INT_MAX) {
                ++i; ++j;
            } else if (nj == INT_MAX) {
                i = ni;
            } else if (ni == INT_MAX) {
                j = nj;
            } else {
                // Choose the smaller skip
                if (nj - j <= ni - i) j = nj;
                else i = ni;
            }
        }
    }

    // Fallback: single-character best
    int bestChar = 0;
    int bestLen = 0;
    for (int c = 0; c < ALPH; ++c) {
        int v = min(cnt1[c], cnt2[c]);
        if (v > bestLen) { bestLen = v; bestChar = c; }
    }
    string single;
    if (bestLen > 0) {
        single.assign(bestLen, (bestChar < 26) ? char('A' + bestChar) : char('0' + (bestChar - 26)));
    }

    if ((int)single.size() > (int)res.size()) {
        cout << single << '\n';
    } else {
        cout << res << '\n';
    }

    return 0;
}