#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    
    long long t = n / 2;   // n/2
    int m0 = sqrt(t);
    while (1LL * (m0+1) * (m0+1) <= t) m0++;
    while (1LL * m0 * m0 > t) m0--;
    
    if (m0 == 0) m0 = 1;   // at least one element
    
    vector<int> S;
    S.reserve(m0);
    
    int max_xor_val = 2 * n;   // safe upper bound for any XOR
    vector<char> seen_xor(max_xor_val + 1, 0);
    
    for (int x = 1; x <= n && (int)S.size() < m0; ++x) {
        bool ok = true;
        for (int y : S) {
            int z = x ^ y;
            if (z <= max_xor_val && seen_xor[z]) {
                ok = false;
                break;
            }
        }
        if (!ok) continue;
        
        // add x to the set
        for (int y : S) {
            int z = x ^ y;
            seen_xor[z] = 1;
        }
        S.push_back(x);
    }
    
    cout << S.size() << "\n";
    for (size_t i = 0; i < S.size(); ++i) {
        if (i > 0) cout << " ";
        cout << S[i];
    }
    cout << "\n";
    
    return 0;
}