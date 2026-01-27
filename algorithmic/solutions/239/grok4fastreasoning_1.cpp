#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    int r = (n + 2) / 3;
    vector<tuple<int, int, int>> triples;
    for (int k = 2; k <= r; ++k) {
        for (int i = 0; i <= n - k; ++i) {
            int u = i;
            int c = i + 1;
            int v = i + k;
            triples.emplace_back(u, c, v);
        }
    }
    cout << triples.size() << endl;
    for (auto [u, c, v] : triples) {
        cout << u << " " << c << " " << v << endl;
    }
    return 0;
}