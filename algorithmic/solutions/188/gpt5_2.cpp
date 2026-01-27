#include <bits/stdc++.h>
using namespace std;

static inline int charId(unsigned char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= '0' && c <= '9') return 26 + (c - '0');
    return -1;
}

static inline char idToChar(int id) {
    if (id < 26) return char('A' + id);
    return char('0' + (id - 26));
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    string s1, s2;
    if (!getline(cin, s1)) s1.clear();
    if (!getline(cin, s2)) s2.clear();
    if (!s1.empty() && s1.back() == '\r') s1.pop_back();
    if (!s2.empty() && s2.back() == '\r') s2.pop_back();

    const int SIG = 36;
    array<vector<int>, SIG> pos1, pos2;
    array<int, SIG> cnt1{}, cnt2{};
    
    // Build position lists and counts
    for (int i = 0; i < (int)s1.size(); ++i) {
        int id = charId((unsigned char)s1[i]);
        if (id >= 0) {
            pos1[id].push_back(i);
            cnt1[id]++;
        }
    }
    for (int j = 0; j < (int)s2.size(); ++j) {
        int id = charId((unsigned char)s2[j]);
        if (id >= 0) {
            pos2[id].push_back(j);
            cnt2[id]++;
        }
    }
    
    // Two-pointer greedy with lookahead using next-occurrence via position lists
    array<int, SIG> pA{}, pB{};
    int i = 0, j = 0;
    const int N = (int)s1.size(), M = (int)s2.size();
    const int INF = INT_MAX;
    string res;
    // Optionally reserve some space; comment out to avoid peak memory
    // res.reserve(min(N, M) / 2);
    
    while (i < N && j < M) {
        unsigned char ca = (unsigned char)s1[i];
        unsigned char cb = (unsigned char)s2[j];
        if (ca == cb) {
            res.push_back((char)ca);
            ++i; ++j;
            continue;
        }
        int id_b = charId(cb);
        int id_a = charId(ca);

        // Next occurrence of s2[j] in s1 starting from i
        int ia = INF;
        if (id_b >= 0) {
            auto &vA = pos1[id_b];
            int &pa = pA[id_b];
            while (pa < (int)vA.size() && vA[pa] < i) ++pa;
            if (pa < (int)vA.size()) ia = vA[pa];
        }

        // Next occurrence of s1[i] in s2 starting from j
        int jb = INF;
        if (id_a >= 0) {
            auto &vB = pos2[id_a];
            int &pb = pB[id_a];
            while (pb < (int)vB.size() && vB[pb] < j) ++pb;
            if (pb < (int)vB.size()) jb = vB[pb];
        }

        if (ia == INF && jb == INF) {
            ++i; ++j;
        } else if (ia == INF) {
            ++j;
        } else if (jb == INF) {
            ++i;
        } else {
            if ((long long)ia - i <= (long long)jb - j) {
                i = ia;
            } else {
                j = jb;
            }
        }
    }

    // Best single-character fallback
    int bestIdx = -1, bestCount = 0;
    for (int k = 0; k < SIG; ++k) {
        int v = min(cnt1[k], cnt2[k]);
        if (v > bestCount) {
            bestCount = v;
            bestIdx = k;
        }
    }

    if (bestCount > (int)res.size()) {
        res.clear();
        res.shrink_to_fit();
        string out(bestCount, idToChar(bestIdx));
        cout << out << '\n';
    } else {
        cout << res << '\n';
    }
    return 0;
}