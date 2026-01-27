#include <bits/stdc++.h>
using namespace std;

inline int idx36(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    return 26 + (c - '0'); // '0'..'9'
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) return 0;

    // Count frequencies for S2
    const int K = 36;
    vector<int> freq(K, 0);
    for (char c : s2) {
        freq[idx36(c)]++;
    }

    // Build position lists for S2
    array<vector<int>, K> pos;
    for (int i = 0; i < K; ++i) pos[i].reserve(freq[i]);
    for (int i = 0; i < (int)s2.size(); ++i) {
        pos[idx36(s2[i])].push_back(i);
    }

    // Pointers into each list
    int ptr[K] = {0};

    // Greedy match s1 into s2
    string res;
    res.reserve(min(s1.size(), s2.size()));
    int j = -1;
    for (char c : s1) {
        int id = idx36(c);
        auto &v = pos[id];
        int &p = ptr[id];
        while (p < (int)v.size() && v[p] <= j) ++p;
        if (p < (int)v.size()) {
            res.push_back(c);
            j = v[p];
            ++p;
        }
    }

    cout << res << '\n';
    return 0;
}