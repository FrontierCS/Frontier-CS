#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int q;
    if (!(cin >> q)) return 0;
    for (int _ = 0; _ < q; ++_) {
        unsigned long long k;
        cin >> k;
        vector<char> ops;
        while (k > 2) {
            if ((k & 1ULL) == 0) {
                ops.push_back('D'); // divide by 2 in reverse -> multiply by 2 forward
                k >>= 1;
            } else {
                ops.push_back('I'); // minus 1 in reverse -> plus 1 forward
                --k;
            }
        }
        vector<int> p;
        p.push_back(0); // leaf with f = 2
        for (int i = (int)ops.size() - 1; i >= 0; --i) {
            if (ops[i] == 'D') {
                // direct sum with a leaf: append value equal to current size
                p.push_back((int)p.size());
            } else {
                // skew sum with a leaf: increment all values by 1, append 0
                for (int &x : p) ++x;
                p.push_back(0);
            }
        }
        cout << p.size() << "\n";
        for (int i = 0; i < (int)p.size(); ++i) {
            if (i) cout << ' ';
            cout << p[i];
        }
        cout << "\n";
    }
    return 0;
}