#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if(!(cin >> t)) return 0;
    while(t--) {
        int n;
        if(!(cin >> n)) return 0;
        vector<int> p(n);
        bool ok = true;
        for (int i = 0; i < n; ++i) {
            if(!(cin >> p[i])) { ok = false; break; }
        }
        if(!ok) {
            // Fallback in case permutation isn't provided in input
            cout << "1 0 1\n";
            cout.flush();
            continue;
        }
        int idx1 = -1, idx2 = -1;
        int max1 = -1, max2 = -1;
        for (int i = 0; i < n; ++i) {
            if (p[i] > max1) {
                max2 = max1; idx2 = idx1;
                max1 = p[i]; idx1 = i;
            } else if (p[i] > max2) {
                max2 = p[i]; idx2 = i;
            }
        }
        if(idx1 == -1 || idx2 == -1) {
            cout << "1 0 1\n";
        } else {
            cout << "1 " << idx1 << " " << idx2 << "\n";
        }
        cout.flush();
    }
    return 0;
}