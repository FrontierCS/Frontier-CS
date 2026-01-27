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
        
        auto query = [&](int i, int j) -> int {
            cout << "? 1 1\n" << i << "\n" << j << "\n";
            cout.flush();
            int F;
            if (!(cin >> F)) exit(0);
            return F;
        };
        
        int a = -1, b = -1;
        // Find two non-demagnetized magnets by pairwise checking
        for (int i = 1; i <= n && a == -1; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                int F = query(i, j);
                if (F != 0) { // both are non-'-'
                    a = i;
                    b = j;
                    break;
                }
            }
        }
        
        vector<int> zeros;
        // Classify each magnet using reference a
        for (int k = 1; k <= n; ++k) {
            if (k == a) continue;
            int F = query(a, k);
            if (F == 0) zeros.push_back(k);
        }
        // Note: a itself could be '-'? No, since a was found in a nonzero pair, it's non-'-'
        
        cout << "! " << zeros.size();
        for (int x : zeros) cout << " " << x;
        cout << "\n";
        cout.flush();
    }
    return 0;
}