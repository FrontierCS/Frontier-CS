#include <bits/stdc++.h>
using namespace std;

int main() {
    int q;
    cin >> q;
    vector<long long> k(q);
    for (int i = 0; i < q; i++) {
        cin >> k[i];
    }
    for (int i = 0; i < q; i++) {
        long long kk = k[i];
        vector<char> ops;
        while (kk > 2) {
            if (kk % 2 == 0) {
                ops.push_back('D');
                kk /= 2;
            } else {
                ops.push_back('A');
                kk -= 1;
            }
        }
        reverse(ops.begin(), ops.end());
        vector<int> p = {0};
        for (char op : ops) {
            int m = p.size();
            if (op == 'D') {
                p.push_back(m);
            } else {
                p.insert(p.begin(), m);
            }
        }
        cout << p.size() << "\n";
        for (size_t j = 0; j < p.size(); j++) {
            if (j > 0) cout << " ";
            cout << p[j];
        }
        cout << "\n";
    }
    return 0;
}