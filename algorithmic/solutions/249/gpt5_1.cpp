#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;
    vector<long long> tokens;
    long long x;
    while (cin >> x) tokens.push_back(x);
    
    long long m = 1LL * n * (n - 1) / 2;
    vector<int> p(n, 0);
    
    if ((long long)tokens.size() >= m) {
        // Interpret as all pairwise ORs in lex order (i<j)
        vector<int> pairVals(m);
        for (long long i = 0; i < m; ++i) pairVals[i] = (int)tokens[i];
        
        vector<long long> sum(n, 0);
        auto offset = [&](int i)->long long {
            return 1LL * i * n - 1LL * i * (i + 1) / 2;
        };
        
        long long idx = 0;
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                int val = pairVals[idx++];
                sum[i] += val;
                sum[j] += val;
            }
        }
        
        long long totalSum = 1LL * n * (n - 1) / 2; // sum of 1..n-1
        int z = -1;
        for (int i = 0; i < n; ++i) {
            if (sum[i] == totalSum) { z = i; break; }
        }
        if (z == -1) {
            // Fallback: if not found (should not happen), output 0..n-1
            for (int i = 0; i < n; ++i) {
                if (i) cout << ' ';
                cout << i;
            }
            cout << '\n';
            return 0;
        }
        
        p[z] = 0;
        for (int j = 0; j < n; ++j) if (j != z) {
            long long id;
            if (z < j) id = offset(z) + (j - z - 1);
            else id = offset(j) + (z - j - 1);
            p[j] = pairVals[id];
        }
        
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << p[i];
        }
        cout << '\n';
    } else if ((int)tokens.size() >= n) {
        // Interpret as permutation directly
        for (int i = 0; i < n; ++i) {
            p[i] = (int)tokens[i];
        }
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << p[i];
        }
        cout << '\n';
    } else {
        // Fallback: output 0..n-1
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << i;
        }
        cout << '\n';
    }
    return 0;
}