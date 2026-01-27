#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, ty;
    if (!(cin >> n >> ty)) return 0;
    
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        if (i == 1) cout << " 0";
        else cout << " 1";
    }
    cout << "\n";
    cout.flush();
    
    return 0;
}