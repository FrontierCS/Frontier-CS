#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    long long m = 1LL * n * (n - 1) / 2;
    vector<int> vals(m);
    for (long long i = 0; i < m; ++i) {
        if (!(cin >> vals[i])) return 0;
    }
    
    // prefix starts for index mapping
    vector<long long> start(n, 0);
    for (int i = 1; i < n; ++i) {
        start[i] = start[i-1] + (n - i);
    }
    auto get_or = [&](int i, int j) -> int {
        if (i == j) return 0;
        if (i > j) swap(i, j);
        return vals[start[i] + (j - i - 1)];
    };
    
    // Find pair (a,b) with minimal OR value (should be 1, from (0,1))
    int a = -1, b = -1;
    int minVal = INT_MAX;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            int v = get_or(i, j);
            if (v < minVal) {
                minVal = v;
                a = i; b = j;
            }
        }
    }
    
    // Determine which one is zero: for zero z and one o, OR(z,k) <= OR(o,k) for all k
    int z = a, o = b;
    bool a_leq_b = true, b_leq_a = true;
    for (int k = 0; k < n; ++k) {
        if (k == a || k == b) continue;
        int va = get_or(a, k);
        int vb = get_or(b, k);
        if (va > vb) a_leq_b = false;
        if (vb > va) b_leq_a = false;
    }
    if (a_leq_b) {
        z = a; o = b;
    } else {
        z = b; o = a;
    }
    
    // Reconstruct permutation
    vector<int> p(n, 0);
    p[z] = 0;
    for (int k = 0; k < n; ++k) {
        if (k == z) continue;
        p[k] = get_or(z, k);
    }
    
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << p[i];
    }
    cout << '\n';
    return 0;
}