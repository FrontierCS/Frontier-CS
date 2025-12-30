#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    int N = n * m;
    vector<int> p(n);
    // For ring 0
    vector<int> as(N + 1);
    for (int k = 1; k <= N; ++k) {
        cout << "? 0 1" << endl;
        cout.flush();
        cin >> as[k];
    }
    as[0] = as[N];
    vector<int> delta(N + 1, 0);
    for (int k = 1; k <= N; ++k) {
        delta[k] = as[k] - as[k - 1];
    }
    int s0 = -1;
    vector<int> F(N, -1);
    bool found = false;
    for (int tau = 0; tau < N; ++tau) {
        if (found) break;
        vector<int> d(N);
        for (int j = 0; j < N; ++j) {
            int kk = ((j - tau + 1LL + N) % N);
            if (kk == 0) kk = N;
            d[j] = delta[kk];
        }
        vector<int> uu(N, -1);
        bool val = true;
        int sumh = 0;
        for (int r = 0; r < m && val; ++r) {
            vector<int> dd(n);
            int sumdd = 0;
            for (int kk = 0; kk < n; ++kk) {
                long long jj = (r + 1LL * kk * m) % N;
                dd[kk] = d[jj];
                sumdd += dd[kk];
            }
            if (sumdd != 0) {
                val = false;
                continue;
            }
            // try v0 = 0
            vector<int> v(n);
            v[0] = 0;
            bool ok = true;
            for (int kk = 0; kk < n - 1; ++kk) {
                v[kk + 1] = v[kk] - dd[kk];
                if (v[kk + 1] < 0 || v[kk + 1] > 1) {
                    ok = false;
                    break;
                }
            }
            if (ok && v[n - 1] - v[0] == dd[n - 1]) {
                // use this
                for (int kk = 0; kk < n; ++kk) {
                    long long jj = (r + 1LL * kk * m) % N;
                    uu[jj] = v[kk];
                }
            } else {
                ok = false;
            }
            if (!ok) {
                // try v0 = 1
                v[0] = 1;
                ok = true;
                for (int kk = 0; kk < n - 1; ++kk) {
                    v[kk + 1] = v[kk] - dd[kk];
                    if (v[kk + 1] < 0 || v[kk + 1] > 1) {
                        ok = false;
                        break;
                    }
                }
                if (ok && v[n - 1] - v[0] == dd[n - 1]) {
                    for (int kk = 0; kk < n; ++kk) {
                        long long jj = (r + 1LL * kk * m) % N;
                        uu[jj] = v[kk];
                    }
                } else {
                    val = false;
                }
            }
        }
        if (!val) continue;
        // now uu is set
        // compute w
        vector<int> w(N, 0);
        for (int pp = 0; pp < N; ++pp) {
            int sm = 0;
            for (int t = 0; t < m; ++t) {
                int jj = (pp + t) % N;
                sm += uu[jj];
            }
            w[pp] = sm;
        }
        int sumh_local = 0;
        for (int j = 0; j < N; ++j) sumh_local += uu[j];
        vector<int> obs_c(N + 1, 0);
        for (int k = 1; k <= N; ++k) {
            obs_c[k] = sumh_local - as[k];
        }
        bool match = true;
        for (int k = 1; k <= N; ++k) {
            int pp = (tau + k) % N;
            if (w[pp] != obs_c[k]) {
                match = false;
                break;
            }
        }
        if (match) {
            s0 = tau;
            F = uu;
            found = true;
        }
    }
    // now s0 and F known
    vector<bool> is_I0(N, false);
    for (int t = 0; t < m; ++t) {
        int jj = (s0 + t) % N;
        is_I0[jj] = true;
    }
    vector<bool> is_F_vec(N, false);
    for (int j = 0; j < N; ++j) {
        if (F[j] == 1) is_F_vec[j] = true;
    }
    vector<int> possible;
    for (int s = 0; s < N; ++s) {
        bool good = true;
        for (int t = 0; t < m; ++t) {
            int jj = (s + t) % N;
            if (is_F_vec[jj]) {
                good = false;
                break;
            }
        }
        if (good) possible.push_back(s);
    }
    int num_pos = possible.size();
    vector<vector<int>> expected(num_pos, vector<int>(N, 0));
    for (int idx = 0; idx < num_pos; ++idx) {
        int s = possible[idx];
        for (int j = 0; j < N; ++j) {
            int pos = (s + j) % N;
            int aa = is_I0[pos] ? 0 : 1;
            int bb = is_F_vec[(pos + m) % N] ? 1 : 0;
            expected[idx][j] = aa - bb;
        }
    }
    // now for each i=1 to n-1
    for (int i = 1; i < n; ++i) {
        // dummy for a0
        cout << "? " << i << " 1" << endl;
        cout.flush();
        int a1;
        cin >> a1;
        cout << "? " << i << " -1" << endl;
        cout.flush();
        int a00;
        cin >> a00;
        vector<int> observed_a{ a00 };
        vector<int> observed_delta;
        vector<int> active = vector<int>(num_pos);
        iota(active.begin(), active.end(), 0);
        int steps_done = 0;
        while (active.size() > 1 && steps_done < N) {
            cout << "? " << i << " 1" << endl;
            cout.flush();
            int new_a;
            cin >> new_a;
            observed_a.push_back(new_a);
            int del_t = new_a - observed_a[steps_done];
            observed_delta.push_back(del_t);
            vector<int> new_active;
            for (int idx : active) {
                if (expected[idx][steps_done] == del_t) {
                    new_active.push_back(idx);
                }
            }
            active = std::move(new_active);
            ++steps_done;
        }
        int chosen_idx = active[0];  // assume size==1
        int si = possible[chosen_idx];
        p[i] = (si - s0 + N) % N;
        // back steps_done times
        for (int b = 0; b < steps_done; ++b) {
            cout << "? " << i << " -1" << endl;
            cout.flush();
            int dum_a;
            cin >> dum_a;
        }
    }
    // output
    cout << "!";
    for (int i = 1; i < n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;
    cout.flush();
    return 0;
}