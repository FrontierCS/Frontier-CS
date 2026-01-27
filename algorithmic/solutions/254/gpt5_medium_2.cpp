#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if(!(cin >> t)) return 0;
    while (t--) {
        int n;
        if(!(cin >> n)) break;
        int m = n * n - n + 1;
        cout << "!";
        for (int i = 1; i <= m; ++i) {
            cout << " " << i;
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}