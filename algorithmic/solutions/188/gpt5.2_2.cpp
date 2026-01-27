#include <bits/stdc++.h>
using namespace std;

static inline int charIndex(unsigned char c) {
    if (c <= '9') return c - '0';
    return c - 'A' + 10;
}

static inline void trimCR(string &s) {
    if (!s.empty() && s.back() == '\r') s.pop_back();
}

static string greedySubseq(const string &a, const string &b) {
    const int SIG = 36;
    array<uint32_t, SIG> cnt{};
    for (unsigned char ch : b) cnt[charIndex(ch)]++;

    array<uint32_t, SIG + 1> start{};
    start[0] = 0;
    for (int k = 0; k < SIG; k++) start[k + 1] = start[k] + cnt[k];

    vector<uint32_t> all;
    all.resize(b.size());

    array<uint32_t, SIG> cur{};
    for (int k = 0; k < SIG; k++) cur[k] = start[k];

    for (uint32_t i = 0; i < (uint32_t)b.size(); i++) {
        int k = charIndex((unsigned char)b[i]);
        all[cur[k]++] = i;
    }

    array<uint32_t, SIG> ptr{};
    for (int k = 0; k < SIG; k++) ptr[k] = start[k];

    string res;
    res.reserve(min(a.size(), b.size()));

    uint32_t j = 0;
    for (unsigned char ch : a) {
        int k = charIndex(ch);
        uint32_t p = ptr[k], e = start[k + 1];

        while (p < e && all[p] < j) ++p;
        if (p < e) {
            res.push_back((char)ch);
            j = all[p] + 1;
            ptr[k] = p + 1;
        } else {
            ptr[k] = p;
        }
        if (j >= (uint32_t)b.size()) break;
    }

    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) s2.clear();
    trimCR(s1);
    trimCR(s2);

    string z1 = greedySubseq(s1, s2);
    string z2 = greedySubseq(s2, s1);

    const string &best = (z2.size() > z1.size()) ? z2 : z1;
    cout.write(best.data(), (streamsize)best.size());
    cout.put('\n');
    return 0;
}