#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if(!(cin >> t)) return 0;
    while (t--) {
        int n;
        if(!(cin >> n)) return 0;
        int m = n * n;
        cout << "! ";
        for (int x = m; x >= n; --x) {
            cout << x << (x == n ? '\n' : ' ');
        }
        cout.flush();
    }
    return 0;
}