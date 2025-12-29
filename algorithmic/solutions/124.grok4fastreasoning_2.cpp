#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<vector<int>> bit(10, vector<int>(n + 1, 0));
    // Level 1: parity, bit 0
    bit[0][1] = 0;
    for (int i = 2; i <= n; ++i) {
        cout << "? 2 1 " << i << endl;
        cout.flush();
        int ans;
        cin >> ans;
        int rr = (ans == 1 ? 0 : 1);
        bit[0][i] = rr;
    }
    // Now current groups: even and odd based on bit[0]
    vector<vector<int>> current_groups(2);
    for (int i = 1; i <= n; ++i) {
        current_groups[bit[0][i]].push_back(i);
    }
    // Levels 2 to 5: bit 1 to 4
    for (int lev = 2; lev <= 5; ++lev) {
        int bidx = lev - 1; // bit bidx
        vector<vector<int>> new_groups;
        for (auto& G : current_groups) {
            int ss = G.size();
            if (ss < 5) continue; // skip small, but won't happen
            // pick c = G[0]
            int cc = G[0];
            // pick 4 more G[1] to G[4]
            vector<int> boot(5);
            for (int t = 0; t < 5; ++t) boot[t] = G[t];
            // 5 leave one out queries
            vector<int> rq(5);
            for (int leave = 0; leave < 5; ++leave) {
                vector<int> sett;
                for (int t = 0; t < 5; ++t) if (t != leave) sett.push_back(boot[t]);
                cout << "? 4";
                for (int x : sett) cout << " " << x;
                cout << endl;
                cout.flush();
                int ans;
                cin >> ans;
                rq[leave] = (ans == 1 ? 0 : 1);
            }
            // c_idx = 0
            int c_idx = 0;
            vector<int> ff(5);
            for (int leave = 0; leave < 5; ++leave) {
                ff[leave] = rq[leave] ^ rq[c_idx];
            }
            // set bit
            for (int t = 0; t < 5; ++t) {
                bit[bidx][boot[t]] = ff[t];
            }
            // now add remaining
            vector<int> known = boot;
            for (int ii = 5; ii < ss; ++ii) {
                int jj = G[ii];
                // 3 known: 0,1,2
                vector<int> sett = {known[0], known[1], known[2], jj};
                cout << "? 4";
                for (int x : sett) cout << " " << x;
                cout << endl;
                cout.flush();
                int ans;
                cin >> ans;
                int rr = (ans == 1 ? 0 : 1);
                int sum_e = bit[bidx][known[0]] ^ bit[bidx][known[1]] ^ bit[bidx][known[2]];
                bit[bidx][jj] = rr ^ sum_e;
            }
            // now split G into sub0 and sub1 based on bit[bidx]
            vector<int> sub0, sub1;
            for (int ii : G) {
                if (bit[bidx][ii] == 0) sub0.push_back(ii);
                else sub1.push_back(ii);
            }
            new_groups.push_back(sub0);
            new_groups.push_back(sub1);
        }
        current_groups = new_groups;
    }
    // Now current_groups are the 32 groups of 25
    vector<long long> p(n + 1);
    int num_groups = current_groups.size();
    for (int g = 0; g < num_groups; ++g) {
        auto& group = current_groups[g];
        int m = group.size(); // 25
        // compute res
        int pos0 = group[0];
        int res = 0;
        for (int kk = 0; kk < 5; ++kk) {
            res += bit[kk][pos0] * (1 << kk);
        }
        // now pair queries
        vector<vector<bool>> is_sum_c(m, vector<bool>(m, false));
        for (int aa = 0; aa < m; ++aa) {
            for (int bb = aa + 1; bb < m; ++bb) {
                vector<int> sett;
                for (int tt = 0; tt < m; ++tt) {
                    if (tt != aa && tt != bb) sett.push_back(group[tt]);
                }
                cout << "? 23";
                for (int x : sett) cout << " " << x;
                cout << endl;
                cout.flush();
                int ans;
                cin >> ans;
                is_sum_c[aa][bb] = (ans == 1);
                is_sum_c[bb][aa] = is_sum_c[aa][bb];
            }
        }
        // now backtracking
        vector<int> assignment(m, -1);
        vector<bool> used(25, false);
        // define lambda for find
        function<bool(int)> find_func = [&](int pos) -> bool {
            if (pos == m) return true;
            for (int jj = 0; jj < 25; ++jj) {
                if (used[jj]) continue;
                bool ok = true;
                for (int pr = 0; pr < pos; ++pr) {
                    int prevj = assignment[pr];
                    int sm = (prevj + jj) % 23;
                    bool actual = (sm == 1);
                    bool required = is_sum_c[pr][pos];
                    if (actual != required) {
                        ok = false;
                        break;
                    }
                }
                if (ok) {
                    assignment[pos] = jj;
                    used[jj] = true;
                    if (find_func(pos + 1)) return true;
                    used[jj] = false;
                    assignment[pos] = -1;
                }
            }
            return false;
        };
        find_func(0);
        // now assignment has the j
        for (int loc = 0; loc < m; ++loc) {
            int glob = group[loc];
            p[glob] = res + 32LL * assignment[loc];
        }
    }
    // now p constructed (base)
    vector<long long> q(n + 1);
    for (int i = 1; i <= n; ++i) {
        q[i] = (long long)n + 1 - p[i];
    }
    // output the one with p[1] <= n/2
    bool use_p = (p[1] <= n / 2);
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << (use_p ? p[i] : q[i]);
    }
    cout << endl;
    cout.flush();
    return 0;
}