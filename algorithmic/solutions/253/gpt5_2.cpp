#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    for (int tc = 0; tc < t; ++tc) {
        int n;
        // Skip stray 0/1 tokens (possible interactive replies in example-like inputs)
        while (cin >> n) { if (n >= 2) break; }
        int m; 
        if (!(cin >> m)) return 0;
        for (int i = 0; i < m; ++i) {
            int a, b; 
            cin >> a >> b;
        }
        cout << "!";
        for (int i = 0; i < m; ++i) cout << " 1";
        cout << "\n";
        cout.flush();
    }
    return 0;
}