#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> a(n);
    for (int i = 0; i < n; i++) {
        cin >> a[i];
    }

    // Choose x = 2 (adjacent swap)
    int x = 2;
    vector<tuple<int, int, int>> operations; // l, r, dir

    // Bubble sort using left shifts of length 2
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n - i - 1; j++) {
            if (a[j] > a[j + 1]) {
                // Swap a[j] and a[j+1] via left shift on interval [j+1, j+2] (1-indexed)
                operations.push_back({j + 1, j + 2, 0});
                swap(a[j], a[j + 1]);
            }
        }
    }

    // Output
    cout << x << " " << operations.size() << "\n";
    for (const auto& op : operations) {
        cout << get<0>(op) << " " << get<1>(op) << " " << get<2>(op) << "\n";
    }

    return 0;
}