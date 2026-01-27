#include <bits/stdc++.h>

using namespace std;

int main() {
    int n;
    cin >> n;
    int mk = (n + 2) / 3;
    vector<tuple<int, int, int>> adds;
    for (int k = 2; k <= mk; ++k) {
        for (int i = 0; i <= n - k; ++i) {
            int b = i + k / 2;
            adds.emplace_back(i, b, i + k);
        }
    }
    cout << adds.size() << '\n';
    for (auto [u, c, v] : adds) {
        cout << u << ' ' << c << ' ' << v << '\n';
    }
    return 0;
}