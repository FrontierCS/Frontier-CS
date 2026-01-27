#include <bits/stdc++.h>
using namespace std;

static inline int charIndex(unsigned char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'A' && c <= 'Z') return 10 + (c - 'A');
    return -1;
}

static inline size_t computeLen(const string &src, const array<vector<int>,36> &pos) {
    array<int,36> ptr{};
    int last = -1;
    size_t len = 0;
    for (unsigned char ch : src) {
        int id = charIndex(ch);
        if (id < 0) continue;
        const vector<int> &v = pos[id];
        int p = ptr[id];
        int sz = (int)v.size();
        while (p < sz && v[p] <= last) ++p;
        if (p < sz) {
            last = v[p];
            ++p;
            ++len;
        }
        ptr[id] = p;
    }
    return len;
}

static inline string computeSeq(const string &src, const array<vector<int>,36> &pos, size_t reserveHint) {
    array<int,36> ptr{};
    int last = -1;
    string out;
    out.reserve(reserveHint);
    for (unsigned char ch : src) {
        int id = charIndex(ch);
        if (id < 0) continue;
        const vector<int> &v = pos[id];
        int p = ptr[id];
        int sz = (int)v.size();
        while (p < sz && v[p] <= last) ++p;
        if (p < sz) {
            last = v[p];
            ++p;
            out.push_back((char)ch);
        }
        ptr[id] = p;
    }
    return out;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) s2.clear();

    array<vector<int>,36> pos1, pos2;
    // Build position lists for s1
    pos1.fill(vector<int>());
    pos2.fill(vector<int>());

    pos1 = {};
    pos2 = {};

    for (int i = 0; i < 36; ++i) {
        pos1[i].reserve(0);
        pos2[i].reserve(0);
    }

    for (int i = 0; i < (int)s1.size(); ++i) {
        int id = charIndex((unsigned char)s1[i]);
        if (id >= 0) pos1[id].push_back(i);
    }
    for (int j = 0; j < (int)s2.size(); ++j) {
        int id = charIndex((unsigned char)s2[j]);
        if (id >= 0) pos2[id].push_back(j);
    }

    // Compute candidate by scanning s1 against s2
    size_t reserveHint = min(s1.size(), s2.size());
    string out1 = computeSeq(s1, pos2, reserveHint);

    // Compute only length for the other direction first
    size_t len2 = computeLen(s2, pos1);

    if (len2 > out1.size()) {
        // Build actual sequence for the second direction
        string out2 = computeSeq(s2, pos1, reserveHint);
        cout << out2;
    } else {
        cout << out1;
    }

    return 0;
}