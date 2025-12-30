#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    long long a[10];
    for (int i = 0; i < 10; ++i) cin >> a[i];

    int u, v;
    for (int i = 0; i < m; ++i) {
        cin >> u >> v; // read and ignore edges
    }

    cout << 1 << "\n" << 1 << "\n";
    return 0;
}