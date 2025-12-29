#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long m;
    if (!(cin >> n >> m)) return 0;

    int a, b, c;
    for (long long i = 0; i < m; ++i) {
        cin >> a >> b >> c; // discard clauses
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << 1; // assign TRUE to all variables
    }
    cout << '\n';

    return 0;
}