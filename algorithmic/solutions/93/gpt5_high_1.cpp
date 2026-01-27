#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, ty;
    if (!(cin >> n >> ty)) return 0;
    cout << '!';
    for (int i = 1; i <= n; ++i) {
        cout << ' ' << (i == 1 ? 0 : 1);
    }
    cout << '\n' << flush;
    return 0;
}