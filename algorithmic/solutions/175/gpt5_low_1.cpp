#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    // Output a simple assignment: all variables set to 1 (TRUE)
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << 1;
    }
    cout << '\n';
    return 0;
}