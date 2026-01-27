#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int L = 0;
    while ((1 << L) < n) ++L;
    if (L == 0) L = 1;

    for (int i = 0; i < n; ++i) {
        string s;
        s.reserve(L);
        for (int b = 0; b < L; ++b) {
            if ((i >> b) & 1) s.push_back('X');
            else s.push_back('O');
        }
        cout << s << "\n";
    }
    cout.flush();

    int q;
    if (!(cin >> q)) return 0;
    long long p;
    for (int i = 0; i < q; ++i) {
        if (!(cin >> p)) return 0;
        cout << 1 << " " << 1 << "\n";
        cout.flush();
    }

    return 0;
}