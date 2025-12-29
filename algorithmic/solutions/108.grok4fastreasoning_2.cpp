#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    int N = n * m;
    int r = 150; // number of deltas

    // Full rotation for ring 0
    vector<int> unblocked(N + 1);
    for (int rot = 1; rot <= N; ++rot) {
        cout << "? 0 1" << endl;
        cout.flush();
        cin >> unblocked[rot];
    }
    // unblocked[1] after 1 rot, ..., unblocked[N] after N rot = u[0]

    vector<int> u(N);
    int min_u = INT_MAX;
    for (int shift = 1; shift < N; ++shift) {
        u[shift] = unblocked[shift];
        min_u = min(min_u, u[shift]);
    }
    u[0] = unblocked[N];
    min_u = min(min_u, u[0]);

    vector<int> o_comp(N);
    for (int pos = 0; pos < N; ++pos) {
        o_comp[pos] = min_u + m - u[pos];
    }

    // Recover c[s]
    vector<int> delta(N);
    for (int k = 0; k < N; ++k) {
        int k1 = (k + 1) % N;
        delta[k] = o_comp[k1] - o_comp[k];
    }

    vector<int> c(N, 0);
    for (int res = 0; res < m; ++res) {
        vector<int> chain_pos(n);
        for (int kk = 0; kk < n; ++kk) {
            chain_pos[kk] = (res + (long long)kk * m) % N;
        }
        vector<int> dd(n);
        for (int kk = 0; kk < n; ++kk) {
            dd[kk] = delta[chain_pos[kk]];
        }
        vector<int> partial(n + 1, 0);
        for (int kk = 0; kk < n; ++kk) {
            partial[kk + 1] = partial[kk] + dd[kk];
        }
        bool ok0 = true;
        for (int kk = 0; kk < n; ++kk) {
            int val = partial[kk];
            if (val < 0 || val > 1) ok0 = false;
        }
        bool ok1 = true;
        for (int kk = 0; kk < n; ++kk) {
            int val = partial[kk] + 1;
            if (val < 0 || val > 1) ok1 = false;
        }
        if (ok0) {
            for (int kk = 0; kk < n; ++kk) {
                c[chain_pos[kk]] = partial[kk];
            }
        } else if (ok1) {
            for (int kk = 0; kk < n; ++kk) {
                c[chain_pos[kk]] = partial[kk] + 1;
            }
        } else {
            // error, but assume ok
            assert(false);
        }
    }

    // Now c[s] recovered, interval0 [0, m-1]

    // precompute d[s] = (c[s] && !(0 <= s && s < m))
    vector<int> d(N, 0);
    for (int s = 0; s < N; ++s) {
        bool in_int0 = (0 <= s && s < m);
        d[s] = (c[s] && !in_int0) ? 1 : 0;
    }

    // prefix_d
    vector<long long> prefix_d(N + 1, 0);
    for (int s = 0; s < N; ++s) {
        prefix_d[s + 1] = prefix_d[s] + d[s];
    }

    // b0[s] = c[s] || in_int0
    vector<int> b0(N, 0);
    for (int s = 0; s < N; ++s) {
        bool in_int0 = (0 <= s && s < m);
        b0[s] = (c[s] || in_int0) ? 1 : 0;
    }

    // prefix_b0
    vector<long long> prefix_b0(N + 1, 0);
    for (int s = 0; s < N; ++s) {
        prefix_b0[s + 1] = prefix_b0[s] + b0[s];
    }

    // precompute o0[q]
    vector<int> o0(N);
    for (int q = 0; q < N; ++q) {
        int ee = (q + m - 1) % N;
        long long sm;
        if (ee >= q) {
            sm = prefix_b0[ee + 1] - prefix_b0[q];
        } else {
            sm = prefix_b0[N] - prefix_b0[q] + prefix_b0[ee + 1] - prefix_b0[0];
        }
        o0[q] = sm;
    }

    // Now for each i=1 to n-1
    vector<int> initial_pos(n); // index 1 to n-1
    int net_r = r; // but since back, net 0
    for (int i = 1; i < n; ++i) {
        // get a0 using ring 0
        cout << "? 0 1" << endl;
        cout.flush();
        int temp;
        cin >> temp;
        cout << "? 0 -1" << endl;
        cout.flush();
        int a_zero;
        cin >> a_zero;

        // now rotate i +1 r times
        vector<int> a(r + 1);
        a[0] = a_zero;
        for (int jj = 1; jj <= r; ++jj) {
            cout << "? " << i << " 1" << endl;
            cout.flush();
            int aa;
            cin >> aa;
            a[jj] = aa;
        }

        // compute obs_delta[0 to r-1]
        vector<int> obs_delta(r);
        for (int jj = 0; jj < r; ++jj) {
            obs_delta[jj] = a[jj + 1] - a[jj];
        }

        // now rotate back -r
        for (int jj = 1; jj <= r; ++jj) {
            cout << "? " << i << " -1" << endl;
            cout.flush();
            int dummy;
            cin >> dummy;
        }

        // now find p
        int best = -1;
        int cnt = 0;
        for (int pp = 0; pp < N; ++pp) {
            // compute exp_o[0 to r]
            vector<int> exp_o(r + 1);
            bool ok = true;
            for (int jj = 0; jj <= r; ++jj) {
                int q = (pp + (long long)jj) % N;
                // sum d in intersection arc(pp, m) and arc(q, m)
                long long numz = 0;
                // get seg for pp
                vector<pair<int, int>> segp = get_segments(pp, m, N);
                // get seg for q
                vector<pair<int, int>> segq = get_segments(q, m, N);
                for (auto [l1, r1] : segp) {
                    for (auto [l2, r2] : segq) {
                        int ll = max(l1, l2);
                        int rr = min(r1, r2);
                        if (ll <= rr) {
                            numz += prefix_d[rr + 1] - prefix_d[ll];
                        }
                    }
                }
                exp_o[jj] = o0[q] - numz;
            }
            // check diffs
            bool match = true;
            for (int jj = 0; jj < r; ++jj) {
                int expd = exp_o[jj + 1] - exp_o[jj];
                if (expd != obs_delta[jj]) {
                    match = false;
                    break;
                }
            }
            if (match) {
                cnt++;
                best = pp;
            }
        }
        initial_pos[i] = best;
        // assume cnt==1
        assert(cnt == 1);
    }

    // now output
    cout << "!";
    for (int i = 1; i < n; ++i) {
        int pi = initial_pos[i] % N;
        if (pi < 0) pi += N;
        cout << " " << pi;
    }
    cout << endl;
    cout.flush();

    return 0;
}

// helper function
vector<pair<int, int>> get_segments(int st, int len, int NN) {
    vector<pair<int, int>> res;
    long long en_ll = ( (long long)st + len - 1 ) % NN;
    int en = en_ll;
    if (en >= st) {
        res.emplace_back(st, en);
    } else {
        res.emplace_back(st, NN - 1);
        res.emplace_back(0, en);
    }
    return res;
}