#include <bits/stdc++.h>
using namespace std;

static int cmap[256];
static vector<int> pos1[36], pos2[36];

inline int c2i(char c) {
    return cmap[(unsigned char)c];
}

string greedy_forward(const string &a, vector<int> posB[], int bLen) {
    string res;
    res.reserve(min(a.size(), (size_t)bLen));
    int ptr[36] = {0};
    int curPos = -1;
    for (char c : a) {
        int id = c2i(c);
        const vector<int> &v = posB[id];
        int &p = ptr[id];
        int sz = (int)v.size();
        while (p < sz && v[p] <= curPos) ++p;
        if (p < sz) {
            curPos = v[p];
            ++p;
            res.push_back(c);
        }
    }
    return res;
}

string greedy_backward(const string &a, vector<int> posB[], int bLen) {
    string rev;
    rev.reserve(min(a.size(), (size_t)bLen));
    int ptr[36];
    for (int i = 0; i < 36; ++i) ptr[i] = (int)posB[i].size() - 1;
    int curPos = bLen;
    for (int i = (int)a.size() - 1; i >= 0; --i) {
        char c = a[i];
        int id = c2i(c);
        const vector<int> &v = posB[id];
        int &p = ptr[id];
        while (p >= 0 && v[p] >= curPos) --p;
        if (p >= 0) {
            curPos = v[p];
            --p;
            rev.push_back(c);
        }
    }
    reverse(rev.begin(), rev.end());
    return rev;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) return 0;

    if (!s1.empty() && s1.back() == '\r') s1.pop_back();
    if (!s2.empty() && s2.back() == '\r') s2.pop_back();

    for (int i = 0; i < 256; ++i) cmap[i] = -1;
    for (char c = 'A'; c <= 'Z'; ++c) cmap[(unsigned char)c] = c - 'A';
    for (char c = '0'; c <= '9'; ++c) cmap[(unsigned char)c] = 26 + (c - '0');

    int n = (int)s1.size();
    int m = (int)s2.size();

    int cnt1[36] = {0}, cnt2[36] = {0};
    for (int i = 0; i < n; ++i) {
        ++cnt1[c2i(s1[i])];
    }
    for (int j = 0; j < m; ++j) {
        ++cnt2[c2i(s2[j])];
    }

    for (int i = 0; i < 36; ++i) {
        pos1[i].reserve(cnt1[i]);
        pos2[i].reserve(cnt2[i]);
    }

    for (int i = 0; i < n; ++i) {
        pos1[c2i(s1[i])].push_back(i);
    }
    for (int j = 0; j < m; ++j) {
        pos2[c2i(s2[j])].push_back(j);
    }

    string best = greedy_forward(s1, pos2, m);

    {
        string cur = greedy_forward(s2, pos1, n);
        if (cur.size() > best.size()) best.swap(cur);
    }

    {
        string cur = greedy_backward(s1, pos2, m);
        if (cur.size() > best.size()) best.swap(cur);
    }

    cout << best << '\n';
    return 0;
}