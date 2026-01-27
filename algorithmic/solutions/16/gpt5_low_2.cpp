#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if(!(cin >> T)) return 0;
    while(T--) {
        long long n;
        if(!(cin >> n)) return 0;
        cout << "! " << 1 << " " << (n >= 3 ? 3 : 1) << "\n" << flush;
        int r;
        if(!(cin >> r)) return 0;
        if(r == -1) return 0;
    }
    return 0;
}