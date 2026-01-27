#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    // Output a simple star centered at node 1 (non-interactive placeholder)
    cout << 1;
    for (int i = 2; i <= n; ++i) {
        cout << " " << 1 << " " << i;
    }
    cout << "\n";
    cout.flush();
    return 0;
}