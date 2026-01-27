#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    
    vector<array<int, 3>> edges;
    
    // Add edges of length 2^k for k >= 1
    for (int k = 1; (1 << k) <= n; ++k) {
        int step = 1 << k;
        for (int i = 0; i + step <= n; ++i) {
            int mid = i + (1 << (k-1));
            edges.push_back({i, mid, i + step});
        }
    }
    
    // Add edges of length 3*2^k for k >= 0
    for (int k = 0; 3 * (1 << k) <= n; ++k) {
        int step = 3 * (1 << k);
        for (int i = 0; i + step <= n; ++i) {
            int mid = i + (1 << k);
            edges.push_back({i, mid, i + step});
        }
    }
    
    cout << edges.size() << "\n";
    for (auto& e : edges) {
        cout << e[0] << " " << e[1] << " " << e[2] << "\n";
    }
    
    return 0;
}