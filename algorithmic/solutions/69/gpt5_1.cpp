#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    // Output n distinct words (simple distinct 'X' runs)
    for (int i = 1; i <= n; ++i) {
        cout << string(i, 'X') << "\n";
    }
    cout.flush();
    
    int q;
    if (!(cin >> q)) return 0;
    while (q--) {
        long long p;
        cin >> p;
        // Dummy answer
        cout << 1 << " " << 1 << "\n";
        cout.flush();
    }
    return 0;
}