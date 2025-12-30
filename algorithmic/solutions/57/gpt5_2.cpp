#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
        }
        cout << "!" ;
        for (int i = 0; i < n; ++i) cout << " 1";
        cout << "\n";
        cout.flush();
    }
    return 0;
}