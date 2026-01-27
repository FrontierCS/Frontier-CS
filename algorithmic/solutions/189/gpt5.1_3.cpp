#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) s2 = "";

    size_t n = s1.size();
    size_t m = s2.size();

    size_t len = max(n, m);
    string out;
    out.reserve(len);

    if (n <= m) {
        out.append(n, 'M');
        out.append(m - n, 'I');
    } else {
        out.append(m, 'M');
        out.append(n - m, 'D');
    }

    cout << out << '\n';
    return 0;
}