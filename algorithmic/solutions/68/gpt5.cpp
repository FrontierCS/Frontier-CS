#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if(!(cin >> t)) return 0;
    while(t--) {
        int n;
        cin >> n;
        vector<int> p(n);
        for(int i = 0; i < n; ++i) cin >> p[i];
        int idx1 = -1, idx2 = -1;
        for(int i = 0; i < n; ++i) {
            if (idx1 == -1 || p[i] > p[idx1]) {
                idx2 = idx1;
                idx1 = i;
            } else if (idx2 == -1 || p[i] > p[idx2]) {
                idx2 = i;
            }
        }
        cout << idx1 << " " << idx2 << "\n";
    }
    return 0;
}