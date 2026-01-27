#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!(cin >> s1)) return 0;
    if (!(cin >> s2)) return 0;

    size_t n = s1.size();
    size_t m = s2.size();

    size_t p = 0;
    while (p < n && p < m && s1[p] == s2[p]) ++p;

    size_t nRem = n - p;
    size_t mRem = m - p;

    size_t s = 0;
    while (s < nRem && s < mRem && s1[n - 1 - s] == s2[m - 1 - s]) ++s;

    size_t midN = n - p - s;
    size_t midM = m - p - s;

    size_t Tlen = (n > m) ? n : m;
    string T;
    T.reserve(Tlen);

    // Prefix matches
    if (p > 0) T.append(p, 'M');

    // Middle region: naive alignment
    size_t midCommon = (midN < midM) ? midN : midM;
    if (midCommon > 0) T.append(midCommon, 'M');
    if (midN > midM) {
        T.append(midN - midM, 'D');
    } else if (midM > midN) {
        T.append(midM - midN, 'I');
    }

    // Suffix matches
    if (s > 0) T.append(s, 'M');

    cout << T << '\n';
    return 0;
}