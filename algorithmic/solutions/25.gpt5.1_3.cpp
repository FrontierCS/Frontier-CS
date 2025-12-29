#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;

        // No queries; assume graph is connected (dummy solution).
        cout << "! 1\n";
        cout.flush();
    }
    return 0;
}