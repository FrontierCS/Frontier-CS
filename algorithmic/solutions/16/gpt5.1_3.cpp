#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        long long n, u, v;
        if (!(cin >> n >> u >> v)) return 0;
        cout << u << " " << v << "\n";
    }

    return 0;
}