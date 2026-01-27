#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    cin >> t;
    for (int test = 0; test < t; ++test) {
        int n;
        cin >> n;
        vector<pair<int, int>> pairs;
        int leftover = -1;
        if (n % 2 == 1) {
            leftover = n;
            for (int i = 1; i <= n - 1; i += 2) {
                pairs.emplace_back(i, i + 1);
            }
        } else {
            for (int i = 1; i <= n; i += 2) {
                pairs.emplace_back(i, i + 1);
            }
        }
        int num_pairs = pairs.size();
        vector<int> ans_pq(num_pairs), ans_qp(num_pairs);
        for (int idx = 0; idx < num_pairs; ++idx) {
            int p = pairs[idx].first, q = pairs[idx].second;
            cout << "? " << p << " " << q << endl << flush;
            int a;
            cin >> a;
            if (a == -1) return 0;
            ans_pq[idx] = a;
            cout << "? " << q << " " << p << endl << flush;
            int b;
            cin >> b;
            if (b == -1) return 0;
            ans_qp[idx] = b;
        }
        int bad_idx = -1;
        for (int idx = 0; idx < num_pairs; ++idx) {
            if (ans_pq[idx] != ans_qp[idx]) {
                bad_idx = idx;
                break;
            }
        }
        int imp;
        if (bad_idx == -1) {
            imp = leftover;
        } else {
            int p = pairs[bad_idx].first;
            int q = pairs[bad_idx].second;
            int a = ans_pq[bad_idx];
            int b = ans_qp[bad_idx];
            int truth_sayer, other;
            if (a == 1 && b == 0) {
                truth_sayer = p;
                other = q;
            } else {
                truth_sayer = q;
                other = p;
            }
            // choose r != p, q
            int r = 1;
            if (r == truth_sayer || r == other) r = 2;
            if (r == truth_sayer || r == other) r = 3;
            // now ask ? truth_sayer r and ? other r
            cout << "? " << truth_sayer << " " << r << endl << flush;
            int ats;
            cin >> ats;
            if (ats == -1) return 0;
            cout << "? " << other << " " << r << endl << flush;
            int ao;
            cin >> ao;
            if (ao == -1) return 0;
            if (ats == ao) {
                imp = truth_sayer;
            } else {
                imp = other;
            }
        }
        cout << "! " << imp << endl << flush;
    }
    return 0;
}