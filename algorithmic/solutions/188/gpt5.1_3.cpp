#include <bits/stdc++.h>
using namespace std;

static inline int cid(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    return 26 + (c - '0'); // '0' - '9'
}

using PosArray = array<vector<int>, 36>;

string forwardMatch(const string &A, const PosArray &posB, int Bsize) {
    int idx[36];
    for (int i = 0; i < 36; ++i) idx[i] = 0;
    int curB = -1;
    size_t cap = A.size() < (size_t)Bsize ? A.size() : (size_t)Bsize;
    string res;
    res.reserve(cap);

    const size_t Asz = A.size();
    for (size_t i = 0; i < Asz; ++i) {
        char ch = A[i];
        int c = cid(ch);
        const vector<int> &vec = posB[c];
        int &p = idx[c];
        int vs = (int)vec.size();
        while (p < vs && vec[p] <= curB) ++p;
        if (p < vs) {
            curB = vec[p++];
            res.push_back(ch);
        }
    }
    return res;
}

string backwardMatch(const string &A, const PosArray &posB, int Bsize) {
    int idx[36];
    for (int i = 0; i < 36; ++i) idx[i] = (int)posB[i].size() - 1;
    int curB = Bsize;
    size_t cap = A.size() < (size_t)Bsize ? A.size() : (size_t)Bsize;
    string revRes;
    revRes.reserve(cap);

    for (int i = (int)A.size() - 1; i >= 0; --i) {
        char ch = A[i];
        int c = cid(ch);
        const vector<int> &vec = posB[c];
        int &p = idx[c];
        while (p >= 0 && vec[p] >= curB) --p;
        if (p >= 0) {
            curB = vec[p--];
            revRes.push_back(ch);
        }
    }
    reverse(revRes.begin(), revRes.end());
    return revRes;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    const size_t MAXN = 30000000;
    s1.reserve(MAXN);
    s2.reserve(MAXN);

    if (!(cin >> s1)) return 0;
    if (!(cin >> s2)) s2.clear();

    int n = (int)s1.size();
    int m = (int)s2.size();

    PosArray pos1, pos2;
    for (int i = 0; i < 36; ++i) {
        pos1[i].clear();
        pos2[i].clear();
    }

    for (int i = 0; i < n; ++i) {
        pos1[cid(s1[i])].push_back(i);
    }
    for (int j = 0; j < m; ++j) {
        pos2[cid(s2[j])].push_back(j);
    }

    string z1 = forwardMatch(s1, pos2, m);
    string z2 = forwardMatch(s2, pos1, n);
    string z3 = backwardMatch(s1, pos2, m);
    string z4 = backwardMatch(s2, pos1, n);

    string *best = &z1;
    if (z2.size() > best->size()) best = &z2;
    if (z3.size() > best->size()) best = &z3;
    if (z4.size() > best->size()) best = &z4;

    cout << *best << '\n';
    return 0;
}