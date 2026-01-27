#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    vector<string> g(30);
    for (int i = 0; i < 30; i++) {
        if (!(cin >> g[i])) return 0;
    }
    string ans(900, '0');
    cout << ans << "\n";
    return 0;
}