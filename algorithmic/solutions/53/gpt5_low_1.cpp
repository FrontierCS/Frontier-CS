#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if(!(cin >> t)) return 0;
    while(t--) {
        int n;
        if(!(cin >> n)) n = 0;
        cout << 1 << "\n";
        cout << "! ";
        for(int i = 1; i <= n; ++i) {
            int val = i % n + 1; // simple derangement shift
            cout << val << (i == n ? '\n' : ' ');
        }
        cout.flush();
    }
    return 0;
}