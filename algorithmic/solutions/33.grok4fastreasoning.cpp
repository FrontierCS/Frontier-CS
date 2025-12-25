#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int q;
    cin >> q;
    vector<long long> ks(q);
    for (int i = 0; i < q; i++) {
        cin >> ks[i];
    }
    
    for (int qi = 0; qi < q; qi++) {
        long long k = ks[qi];
        long long cur = k;
        vector<int> ops;
        while (cur > 1) {
            if (cur % 2 == 1) {
                ops.push_back(1); // low
                cur--;
            } else {
                ops.push_back(0); // high
                cur /= 2;
            }
        }
        int n = ops.size();
        vector<int> p(n);
        vector<int> low_pos, high_pos;
        for (int i = 0; i < n; i++) {
            int op = ops[n - 1 - i];
            if (op == 1) {
                low_pos.push_back(i);
            } else {
                high_pos.push_back(i);
            }
        }
        int l = low_pos.size();
        int h = high_pos.size();
        for (int j = 0; j < l; j++) {
            int pos = low_pos[j];
            p[pos] = l - 1 - j;
        }
        for (int j = 0; j < h; j++) {
            int pos = high_pos[j];
            p[pos] = l + j;
        }
        cout << n << '\n';
        for (int i = 0; i < n; i++) {
            if (i > 0) cout << ' ';
            cout << p[i];
        }
        cout << '\n';
    }
    return 0;
}