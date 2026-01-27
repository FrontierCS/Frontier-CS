#include <bits/stdc++.h>
using namespace std;

static const int ALPHA = 36;
int charToIdx[256];

inline int idx(unsigned char c) {
    return charToIdx[c];
}

string greedy(const string &s1, const string &s2, const int freq1[], const int freq2[]) {
    int rem1[ALPHA], rem2[ALPHA], pot[ALPHA];
    for (int c = 0; c < ALPHA; ++c) {
        rem1[c] = freq1[c];
        rem2[c] = freq2[c];
        pot[c] = rem1[c] < rem2[c] ? rem1[c] : rem2[c];
    }

    int n = (int)s1.size();
    int m = (int)s2.size();
    string res;
    res.reserve(min(n, m));

    int i = 0, j = 0;
    while (i < n && j < m) {
        unsigned char ca = (unsigned char)s1[i];
        unsigned char cb = (unsigned char)s2[j];
        if (ca == cb) {
            int id = idx(ca);
            res.push_back((char)ca);
            --rem1[id];
            --rem2[id];
            pot[id] = rem1[id] < rem2[id] ? rem1[id] : rem2[id];
            ++i;
            ++j;
        } else {
            int ia = idx(ca);
            int ib = idx(cb);
            if (rem2[ia] == 0) {
                --rem1[ia];
                pot[ia] = rem1[ia] < rem2[ia] ? rem1[ia] : rem2[ia];
                ++i;
            } else if (rem1[ib] == 0) {
                --rem2[ib];
                pot[ib] = rem1[ib] < rem2[ib] ? rem1[ib] : rem2[ib];
                ++j;
            } else {
                if (pot[ia] < pot[ib]) {
                    --rem1[ia];
                    pot[ia] = rem1[ia] < rem2[ia] ? rem1[ia] : rem2[ia];
                    ++i;
                } else if (pot[ib] < pot[ia]) {
                    --rem2[ib];
                    pot[ib] = rem1[ib] < rem2[ib] ? rem1[ib] : rem2[ib];
                    ++j;
                } else {
                    if ((n - i) > (m - j)) {
                        --rem1[ia];
                        pot[ia] = rem1[ia] < rem2[ia] ? rem1[ia] : rem2[ia];
                        ++i;
                    } else {
                        --rem2[ib];
                        pot[ib] = rem1[ib] < rem2[ib] ? rem1[ib] : rem2[ib];
                        ++j;
                    }
                }
            }
        }
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    for (int i = 0; i < 256; ++i) charToIdx[i] = 0;
    for (char c = 'A'; c <= 'Z'; ++c)
        charToIdx[(unsigned char)c] = c - 'A';
    for (char c = '0'; c <= '9'; ++c)
        charToIdx[(unsigned char)c] = 26 + (c - '0');

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) s2.clear();

    int freq1[ALPHA] = {0};
    int freq2[ALPHA] = {0};

    for (size_t i = 0; i < s1.size(); ++i)
        ++freq1[idx((unsigned char)s1[i])];
    for (size_t i = 0; i < s2.size(); ++i)
        ++freq2[idx((unsigned char)s2[i])];

    string res1 = greedy(s1, s2, freq1, freq2);
    string res2 = greedy(s2, s1, freq2, freq1);

    const string &best = (res1.size() >= res2.size()) ? res1 : res2;
    cout << best << '\n';
    return 0;
}