#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    while (cin >> n) {
        int bits = 0;
        while ((1 << bits) < n) bits++;
        int mask = (1 << bits) - 1;
        vector<int> p(n, mask);
        
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                int x;
                if (!(cin >> x)) return 0;
                p[i] &= x;
                p[j] &= x;
            }
        }
        
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << p[i];
        }
        cout << '\n';
    }
    return 0;
}