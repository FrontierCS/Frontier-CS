#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

vector<int> construct_perm(ll k) {
    // backward operations
    vector<char> ops;
    while (k > 1) {
        if (k & 1) {
            ops.push_back('a');  // add (min)
            k--;
        } else {
            ops.push_back('m');  // multiply (max)
            k /= 2;
        }
    }
    reverse(ops.begin(), ops.end());

    // simulate insertion
    int minVal = 0, maxVal = 0;
    vector<int> vals;
    for (char op : ops) {
        if (op == 'm') {
            int val = maxVal + 1;
            vals.push_back(val);
            maxVal = val;
        } else {
            int val = minVal - 1;
            vals.push_back(val);
            minVal = val;
        }
    }

    // compress values to 0..n-1
    vector<int> sorted = vals;
    sort(sorted.begin(), sorted.end());
    unordered_map<int, int> rank;
    for (size_t i = 0; i < sorted.size(); ++i)
        rank[sorted[i]] = i;

    vector<int> perm;
    for (int v : vals)
        perm.push_back(rank[v]);
    return perm;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int q;
    cin >> q;
    vector<ll> ks(q);
    for (int i = 0; i < q; ++i)
        cin >> ks[i];

    for (ll k : ks) {
        vector<int> perm = construct_perm(k);
        cout << perm.size() << "\n";
        for (size_t i = 0; i < perm.size(); ++i) {
            if (i) cout << " ";
            cout << perm[i];
        }
        cout << "\n";
    }
    return 0;
}