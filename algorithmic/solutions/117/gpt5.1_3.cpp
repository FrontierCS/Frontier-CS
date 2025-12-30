#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    cout << "!";
    for (int i = 0; i < 2 * n; ++i) {
        cout << " 0";
    }
    cout << "\n";
    return 0;
}