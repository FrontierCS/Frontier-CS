#include <bits/stdc++.h>
using namespace std;

inline int cid(char c) {
    if (c >= 'A') return c - 'A';        // 'A'-'Z' -> 0..25
    return 26 + (c - '0');              // '0'-'9' -> 26..35
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) s2 = "";

    if (!s1.empty() && s1.back() == '\r') s1.pop_back();
    if (!s2.empty() && s2.back() == '\r') s2.pop_back();

    string *pa = &s1, *pb = &s2;
    if (s1.size() < s2.size()) {
        pa = &s2;
        pb = &s1;
    }
    const string &A = *pa;
    const string &B = *pb;

    const int ALPH = 36;
    vector<int> freq(ALPH, 0);

    for (char c : B) {
        freq[cid(c)]++;
    }

    vector<int> pos[ALPH];
    for (int i = 0; i < ALPH; ++i) {
        if (freq[i] > 0) pos[i].reserve(freq[i]);
    }

    for (int i = 0; i < (int)B.size(); ++i) {
        pos[cid(B[i])].push_back(i);
    }

    vector<int> idx(ALPH, 0);
    string res;
    res.reserve(min(A.size(), B.size()));

    int cur2 = 0;
    int bsz = (int)B.size();

    for (int i = 0; i < (int)A.size() && cur2 < bsz; ++i) {
        int id = cid(A[i]);
        auto &vec = pos[id];
        int &p = idx[id];
        while (p < (int)vec.size() && vec[p] < cur2) ++p;
        if (p == (int)vec.size()) continue;
        res.push_back(A[i]);
        cur2 = vec[p] + 1;
        ++p;
    }

    cout << res << '\n';
    return 0;
}