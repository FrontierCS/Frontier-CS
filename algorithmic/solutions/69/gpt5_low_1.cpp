#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;
    // Output n distinct words over {X, O}, lengths within [1, 30n]
    // Simple distinct strings: "X", "XX", ..., "X...X", and then add 'O's to ensure distinctness if needed
    for(int i = 1; i <= n; ++i) {
        string s;
        int len = min(30 * n, i);
        s.assign(len, 'X');
        cout << s << "\n";
    }
    cout.flush();
    
    int q;
    if(!(cin >> q)) return 0;
    while(q--) {
        long long p; 
        cin >> p;
        // Placeholder response
        cout << 1 << " " << 1 << "\n";
        cout.flush();
    }
    return 0;
}