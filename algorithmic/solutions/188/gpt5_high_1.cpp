#include <bits/stdc++.h>
using namespace std;

static inline int charIndex(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= '0' && c <= '9') return 26 + (c - '0');
    return -1;
}
static inline char indexChar(int idx) {
    return (idx < 26) ? char('A' + idx) : char('0' + (idx - 26));
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    getline(cin, s2);

    if (!s1.empty() && s1.back() == '\r') s1.pop_back();
    if (!s2.empty() && s2.back() == '\r') s2.pop_back();

    const int ALPHA = 36;

    // Count occurrences
    vector<int> cnt1(ALPHA, 0), cnt2(ALPHA, 0);
    for (char c : s1) {
        int id = charIndex(c);
        if (id >= 0) cnt1[id]++;
    }
    for (char c : s2) {
        int id = charIndex(c);
        if (id >= 0) cnt2[id]++;
    }

    // Build position lists
    vector<int> pos1[ALPHA], pos2[ALPHA];
    for (int i = 0; i < ALPHA; ++i) {
        if (cnt1[i] > 0) pos1[i].reserve(cnt1[i]);
        if (cnt2[i] > 0) pos2[i].reserve(cnt2[i]);
    }
    for (int i = 0; i < (int)s1.size(); ++i) {
        int id = charIndex(s1[i]);
        if (id >= 0) pos1[id].push_back(i);
    }
    for (int i = 0; i < (int)s2.size(); ++i) {
        int id = charIndex(s2[i]);
        if (id >= 0) pos2[id].push_back(i);
    }

    // Free original strings to save memory
    {
        string().swap(s1);
        string().swap(s2);
    }

    // Best single-character fallback
    int bestSingleChar = -1;
    int bestSingleCount = 0;
    for (int i = 0; i < ALPHA; ++i) {
        int k = min(cnt1[i], cnt2[i]);
        if (k > bestSingleCount) {
            bestSingleCount = k;
            bestSingleChar = i;
        }
    }

    // Greedy mutual-earliest heuristic
    vector<int> idx1(ALPHA, 0), idx2(ALPHA, 0);
    int iPos = 0, jPos = 0;
    string out;
    // Optionally reserve a reasonable amount to reduce reallocations
    // but avoid over-reserving huge memory unnecessarily.
    // We'll reserve min(bestSingleCount * 2, 1'000'000) as a heuristic.
    if (bestSingleCount > 0) out.reserve(min(bestSingleCount * 2, 1000000));

    while (true) {
        // advance pointers for all characters to be >= current positions
        for (int c = 0; c < ALPHA; ++c) {
            auto &v1 = pos1[c];
            auto &v2 = pos2[c];
            int &p1 = idx1[c];
            int &p2 = idx2[c];
            while (p1 < (int)v1.size() && v1[p1] < iPos) ++p1;
            while (p2 < (int)v2.size() && v2[p2] < jPos) ++p2;
        }

        int bestC = -1;
        int bestMaxD = INT_MAX;
        int bestSumD = INT_MAX;
        int bestMinD = INT_MAX;

        for (int c = 0; c < ALPHA; ++c) {
            auto &v1 = pos1[c];
            auto &v2 = pos2[c];
            int p1 = idx1[c];
            int p2 = idx2[c];
            if (p1 >= (int)v1.size() || p2 >= (int)v2.size()) continue;
            int d1 = v1[p1] - iPos;
            int d2 = v2[p2] - jPos;
            int maxd = d1 > d2 ? d1 : d2;
            int sumd = d1 + d2;
            int mind = d1 < d2 ? d1 : d2;

            if (maxd < bestMaxD ||
                (maxd == bestMaxD && (sumd < bestSumD ||
                 (sumd == bestSumD && (mind < bestMinD ||
                  (mind == bestMinD && c < bestC))))))
            {
                bestMaxD = maxd;
                bestSumD = sumd;
                bestMinD = mind;
                bestC = c;
            }
        }

        if (bestC == -1) break;

        int p1 = pos1[bestC][idx1[bestC]];
        int p2 = pos2[bestC][idx2[bestC]];
        out.push_back(indexChar(bestC));
        iPos = p1 + 1;
        jPos = p2 + 1;
        idx1[bestC]++;
        idx2[bestC]++;
    }

    // Choose better between heuristic output and single-char fallback
    if ((int)out.size() < bestSingleCount) {
        string res(bestSingleCount, indexChar(bestSingleChar));
        cout << res << '\n';
    } else {
        cout << out << '\n';
    }

    return 0;
}