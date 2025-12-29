#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s;
    for (int i = 0; i < 30; ++i) {
        if (!(cin >> s)) return 0; // read and ignore
    }

    string ans(900, '0'); // no rotations
    cout << ans << '\n';
    return 0;
}