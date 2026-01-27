#include <bits/stdc++.h>
using namespace std;

static inline int charIndex(unsigned char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= '0' && c <= '9') return 26 + (c - '0');
    return -1;
}

using PosArray = array<vector<int>, 36>;

static void buildPositions(const string &s, PosArray &pos) {
    array<int, 36> cnt{};
    for (unsigned char ch : s) {
        int ci = charIndex(ch);
        if (ci >= 0) ++cnt[ci];
    }
    for (int i = 0; i < 36; ++i) {
        pos[i].clear();
        pos[i].reserve(cnt[i]);
    }
    int i = 0;
    for (unsigned char ch : s) {
        int ci = charIndex(ch);
        if (ci >= 0) pos[ci].push_back(i);
        ++i;
    }
}

static string greedyMatch(const string &A, const PosArray &posB, size_t Bsize) {
    array<int, 36> ptr{};
    int last = -1;
    string res;
    res.reserve(min(A.size(), Bsize));
    for (unsigned char ch : A) {
        int ci = charIndex(ch);
        if (ci < 0) continue;
        const auto &v = posB[ci];
        int p = ptr[ci];
        while (p < (int)v.size() && v[p] <= last) ++p;
        if (p < (int)v.size()) {
            res.push_back((char)ch);
            last = v[p];
            ++p;
        }
        ptr[ci] = p;
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) s1.clear();
    if (!getline(cin, s2)) s2.clear();

    PosArray pos;

    // Pass 1: positions of s2, match s1 -> s2
    buildPositions(s2, pos);
    string z1 = greedyMatch(s1, pos, s2.size());

    // Pass 2: positions of s1, match s2 -> s1
    buildPositions(s1, pos);
    string z2 = greedyMatch(s2, pos, s1.size());

    const string &best = (z2.size() > z1.size()) ? z2 : z1;

    cout.write(best.data(), (streamsize)best.size());
    cout.put('\n');
    return 0;
}