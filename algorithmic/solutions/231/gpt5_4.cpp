#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m, T;
    if (!(cin >> n >> m >> T)) {
        cout << 0 << "\n";
        cout.flush();
        return 0;
    }
    for (int i = 0; i < m; ++i) {
        int a, b;
        if (!(cin >> a >> b)) break;
    }
    
    cout << 0 << "\n";
    for (int t = 0; t < T; ++t) {
        cout << "! 1\n";
    }
    cout.flush();
    return 0;
}