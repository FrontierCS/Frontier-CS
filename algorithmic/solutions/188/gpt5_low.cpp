#include <bits/stdc++.h>
using namespace std;

static inline int cmap(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    return 26 + (c - '0'); // '0'-'9'
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) return 0;

    const int SIG = 36;
    vector<size_t> freq(SIG, 0);
    for (char c : s1) freq[cmap(c)]++;

    vector<vector<int>> pos(SIG);
    for (int i = 0; i < SIG; ++i) pos[i].reserve(freq[i]);

    for (int i = 0; i < (int)s1.size(); ++i) {
        pos[cmap(s1[i])].push_back(i);
    }

    vector<size_t> ptr(SIG, 0);
    string res;
    res.reserve(min(s1.size(), s2.size()));
    int last = -1;

    for (char c : s2) {
        int id = cmap(c);
        auto &v = pos[id];
        size_t &p = ptr[id];
        while (p < v.size() && v[p] <= last) ++p;
        if (p < v.size()) {
            last = v[p];
            ++p;
            res.push_back(c);
        }
    }

    cout << res << '\n';
    return 0;
}