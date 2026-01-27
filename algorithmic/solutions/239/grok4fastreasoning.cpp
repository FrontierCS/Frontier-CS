#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    if (n <= 3) {
        cout << 0 << endl;
        return 0;
    }
    int l = (n + 2) / 3;
    vector<tuple<int, int, int>> adds;
    for (int k = 2; k <= l; ++k) {
        for (int i = 0; i <= n - k; ++i) {
            adds.emplace_back(i, i + 1, i + k);
        }
    }
    cout << adds.size() << endl;
    for (auto [u, c, v] : adds) {
        cout << u << " " << c << " " << v << endl;
    }
    return 0;
}