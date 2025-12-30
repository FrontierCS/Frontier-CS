#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long k, n;
    if (!(cin >> k >> n)) return 0;

    cout << "! ";
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << i;
    }
    cout << "\n";
    cout.flush();
    return 0;
}