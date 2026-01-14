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
        cout << 1 << endl;
        cout.flush();
        vector<int> perm(n + 1);
        int query_count = 0;
        int max_queries = 10 * n;
        for (int x = 1; x <= n; ++x) {
            vector<int> others;
            for (int i = 1; i <= n; ++i) {
                if (i != x) others.push_back(i);
            }
            sort(others.begin(), others.end());
            int N = others.size();
            // Choose ms using powers of 2 and some additional points
            set<int> mset;
            mset.insert(1);
            for (int p = 2; p <= N; p *= 2) {
                mset.insert(p);
            }
            if (N >= 2) mset.insert(2);
            if (N >= 3) mset.insert(3);
            if (N >= 5) mset.insert(5);
            if (N >= N / 2) mset.insert(N / 2);
            if (N >= N / 3) mset.insert(N / 3);
            if (N >= 3 * N / 4) mset.insert(3 * N / 4);
            if (N >= N - 1) mset.insert(N);
            vector<int> ms(mset.begin(), mset.end());
            // Ensure at least 1 and at most 9 base queries
            if (ms.empty()) ms.push_back(1);
            while (ms.size() > 9) ms.resize(9);
            int num_base = ms.size();
            vector<long long> Cs(num_base, 0);
            for (int i = 0; i < num_base; ++i) {
                if (query_count >= max_queries) {
                    return 0;
                }
                int m = ms[i];
                vector<int> qq(n);
                int idx = 0;
                for (int j = 0; j < m; ++j) {
                    qq[idx++] = others[j];
                }
                qq[idx++] = x;
                for (int j = m; j < N; ++j) {
                    qq[idx++] = others[j];
                }
                cout << "?";
                for (int val : qq) {
                    cout << " " << val;
                }
                cout << endl;
                cout.flush();
                long long c;
                cin >> c;
                if (c == -1 || cin.eof()) {
                    return 0;
                }
                Cs[i] = c;
                ++query_count;
            }
            // Reference is first
            int ref_i = 0;
            vector<long long> ds(num_base);
            for (int i = 0; i < num_base; ++i) {
                ds[i] = Cs[i] - Cs[ref_i];
            }
            // Available for extra
            set<int> available;
            for (int i = 1; i <= N; ++i) {
                if (mset.find(i) == mset.end()) {
                    available.insert(i);
                }
            }
            // Find candidates
            vector<pair<int, int>> cands;
            for (int rr = 1; rr <= N; ++rr) {
                for (int tt = 1; tt <= N; ++tt) {
                    if (rr == tt) continue;
                    int vvref = ((ms[ref_i] < tt) ? 1 : 0) + ((ms[ref_i] >= rr) ? 1 : 0);
                    bool ok = true;
                    for (int j = 0; j < num_base; ++j) {
                        int vv = ((ms[j] < tt) ? 1 : 0) + ((ms[j] >= rr) ? 1 : 0);
                        if (vv - vvref != ds[j]) {
                            ok = false;
                            break;
                        }
                    }
                    if (ok) {
                        cands.emplace_back(rr, tt);
                    }
                }
            }
            // Now resolve if necessary
            vector<int> ms_all = ms;
            vector<long long> Cs_all = Cs;
            while (cands.size() > 1 && !available.empty() && query_count < max_queries) {
                int new_m = *available.begin();
                available.erase(available.begin());
                // Query
                vector<int> qq(n);
                int idx = 0;
                for (int j = 0; j < new_m; ++j) {
                    qq[idx++] = others[j];
                }
                qq[idx++] = x;
                for (int j = new_m; j < N; ++j) {
                    qq[idx++] = others[j];
                }
                cout << "?";
                for (int val : qq) {
                    cout << " " << val;
                }
                cout << endl;
                cout.flush();
                long long c_new;
                cin >> c_new;
                if (c_new == -1 || cin.eof()) {
                    return 0;
                }
                ++query_count;
                long long d_new = c_new - Cs_all[ref_i];
                // Filter
                vector<pair<int, int>> new_cands;
                for (auto [rr, tt] : cands) {
                    int vvref = ((ms_all[ref_i] < tt) ? 1 : 0) + ((ms_all[ref_i] >= rr) ? 1 : 0);
                    int vv = ((new_m < tt) ? 1 : 0) + ((new_m >= rr) ? 1 : 0);
                    if (vv - vvref == d_new) {
                        new_cands.emplace_back(rr, tt);
                    }
                }
                cands = move(new_cands);
                // Add to all
                ms_all.push_back(new_m);
                Cs_all.push_back(c_new);
            }
            // Now should be 1
            assert(cands.size() == 1);
            int tt = cands[0].second;
            perm[x] = others[tt - 1];
        }
        // Output
        cout << "!";
        for (int i = 1; i <= n; ++i) {
            cout << " " << perm[i];
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}