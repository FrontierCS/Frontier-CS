#include <bits/stdc++.h>
using namespace std;
using ll = long long;

vector<int> construct_perm(ll k) {
    if (k == 2) {
        return {0};
    }
    vector<char> ops;
    while (k > 2) {
        if (k % 2 == 1) {
            ops.push_back('A');
            k--;
        } else {
            ops.push_back('D');
            k /= 2;
        }
    }
    reverse(ops.begin(), ops.end());
    deque<int> dq;
    dq.push_back(0);
    int cur_min = 0, cur_max = 0;
    for (char op : ops) {
        if (op == 'D') {
            int new_val = cur_max + 1;
            dq.push_back(new_val);
            cur_max = new_val;
        } else {
            int new_val = cur_min - 1;
            dq.push_back(new_val);
            cur_min = new_val;
        }
    }
    vector<int> perm(dq.begin(), dq.end());
    int shift = -cur_min;
    for (int &x : perm) x += shift;
    return perm;
}

int main() {
    int q;
    cin >> q;
    vector<ll> ks(q);
    for (int i = 0; i < q; i++) {
        cin >> ks[i];
    }
    for (ll k : ks) {
        vector<int> perm = construct_perm(k);
        int n = perm.size();
        cout << n << "\n";
        for (int i = 0; i < n; i++) {
            if (i > 0) cout << " ";
            cout << perm[i];
        }
        cout << "\n";
    }
    return 0;
}