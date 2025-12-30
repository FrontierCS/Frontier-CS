#include <bits/stdc++.h>
using namespace std;

vector<int> get_runs(long long k) {
    vector<int> res;
    if (k == 2) {
        res.push_back(1);
        return res;
    }
    int m = 0;
    long long pw = 1;
    while (pw <= k / 2) {
        pw *= 2;
        m++;
    }
    if (pw == k) {
        res.push_back(m);
        return res;
    }
    long long small_k = k - pw + 1;
    vector<int> small = get_runs(small_k);
    res.push_back(m);
    res.insert(res.end(), small.begin(), small.end());
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int q;
    cin >> q;
    vector<long long> ks(q);
    for (int i = 0; i < q; i++) {
        cin >> ks[i];
    }
    for (int iq = 0; iq < q; iq++) {
        long long k = ks[iq];
        vector<int> runs = get_runs(k);
        int n = 0;
        for (int l : runs) n += l;
        vector<int> perm(n);
        int cur_val = n - 1;
        int pos = 0;
        for (int len : runs) {
            int block_low = cur_val - len + 1;
            for (int j = 0; j < len; j++) {
                perm[pos++] = block_low + j;
            }
            cur_val = block_low - 1;
        }
        cout << n << '\n';
        for (int i = 0; i < n; i++) {
            if (i > 0) cout << " ";
            cout << perm[i];
        }
        cout << '\n';
    }
    return 0;
}