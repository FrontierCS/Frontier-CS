#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    string W;
    if (!(cin >> n >> W)) return 0;
    string x;
    for (int i = 0; i < n; i++) cin >> x;

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << 0;
    }
    cout << '\n';
    return 0;
}