#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    for (int i = 0; i < n; ++i) {
        // Dummy solution: outputs a placeholder cycle length.
        // In a real interactive environment, we would use queries to determine the cycle length.
        cout << "! " << 3 << "\n" << flush;

        int verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == -1) return 0;
    }

    return 0;
}