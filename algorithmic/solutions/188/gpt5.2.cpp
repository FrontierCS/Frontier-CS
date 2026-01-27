#include <bits/stdc++.h>
using namespace std;

static array<int, 256> buildCharMap() {
    array<int, 256> mp;
    mp.fill(-1);
    for (int c = '0'; c <= '9'; ++c) mp[(unsigned char)c] = c - '0';
    for (int c = 'A'; c <= 'Z'; ++c) mp[(unsigned char)c] = 10 + (c - 'A');
    return mp;
}

static const array<int, 256> CHAR_MAP = buildCharMap();

static string greedyMatch(const string& A, const string& B) {
    array<uint32_t, 36> cnt{};
    cnt.fill(0);

    for (unsigned char ch : B) {
        int idx = CHAR_MAP[ch];
        if (idx >= 0) ++cnt[idx];
    }

    array<vector<int32_t>, 36> pos;
    for (int i = 0; i < 36; ++i) pos[i].reserve(cnt[i]);

    for (int32_t i = 0, n = (int32_t)B.size(); i < n; ++i) {
        unsigned char ch = (unsigned char)B[(size_t)i];
        int idx = CHAR_MAP[ch];
        if (idx >= 0) pos[idx].push_back(i);
    }

    array<size_t, 36> ptr{};
    ptr.fill(0);

    string res;
    res.reserve(min(A.size(), B.size()));

    int32_t p = -1;
    for (unsigned char ch : A) {
        int idx = CHAR_MAP[ch];
        if (idx < 0) continue;

        auto &v = pos[idx];
        size_t &t = ptr[idx];
        while (t < v.size() && v[t] <= p) ++t;
        if (t < v.size()) {
            p = v[t];
            ++t;
            res.push_back((char)ch);
        }
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!(cin >> s1)) return 0;
    if (!(cin >> s2)) return 0;

    string r1 = greedyMatch(s1, s2);
    string r2 = greedyMatch(s2, s1);

    const string& best = (r2.size() > r1.size()) ? r2 : r1;

    cout.write(best.data(), (streamsize)best.size());
    cout.put('\n');
    return 0;
}