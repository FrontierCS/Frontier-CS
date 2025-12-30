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
        for(int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
        }
        long long mole;
        if(!(cin >> mole)) mole = 1;
        cout << mole << "\n";
    }
    return 0;
}