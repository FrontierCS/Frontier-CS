#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) s2 = "";

    size_t n = s1.size(), m = s2.size();
    string T;
    T.reserve(n + m);

    size_t common = min(n, m);
    T.append(common, 'M');
    if (n > common) T.append(n - common, 'D');
    if (m > common) T.append(m - common, 'I');

    cout << T << '\n';
    return 0;
}