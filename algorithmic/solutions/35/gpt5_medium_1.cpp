#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    for (int _ = 0; _ < t; ++_) {
        int n;
        if (!(cin >> n)) return 0;
        int k;
        if (!(cin >> k)) return 0; // read handshake (usually 0), or -1 on failure
        if (k == -1) return 0;
        cout << "! " << 1 << endl;
        cout.flush();
    }
    return 0;
}