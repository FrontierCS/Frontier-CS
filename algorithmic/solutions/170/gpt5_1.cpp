#include <bits/stdc++.h>
using namespace std;

static const double EPS = 1e-15;

vector<double> compute_stationary(const vector<int>& a, const vector<int>& b) {
    int N = (int)a.size();
    vector<double> v(N, 1.0 / N), nv(N), tmp(N);
    for (int it = 0; it < 2000; ++it) {
        fill(tmp.begin(), tmp.end(), 0.0);
        for (int j = 0; j < N; ++j) {
            tmp[a[j]] += 0.5 * v[j];
            tmp[b[j]] += 0.5 * v[j];
        }
        double diff = 0.0, sum = 0.0;
        for (int i = 0; i < N; ++i) {
            nv[i] = 0.5 * v[i] + 0.5 * tmp[i];
            sum += nv[i];
        }
        // Normalize just in case of numerical drift
        if (sum > 0) {
            for (int i = 0; i < N; ++i) nv[i] /= sum;
        }
        for (int i = 0; i < N; ++i) diff += fabs(nv[i] - v[i]);
        v.swap(nv);
        if (diff < 1e-14) break;
    }
    // final normalization
    double sum = accumulate(v.begin(), v.end(), 0.0);
    if (sum > 0) for (int i = 0; i < N; ++i) v[i] /= sum;
    return v;
}

vector<int> assign_b_by_greedy(const vector<double>& w, const vector<double>& S) {
    int N = (int)w.size();
    vector<double> R = S;
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int i, int j){
        if (w[i] != w[j]) return w[i] > w[j];
        return i < j;
    });
    vector<int> b(N, 0);
    for (int idx = 0; idx < N; ++idx) {
        int j = order[idx];
        // choose i with maximum residual R[i]
        int bi = 0;
        double best = R[0];
        for (int i = 1; i < N; ++i) {
            if (R[i] > best + 1e-18) {
                best = R[i];
                bi = i;
            }
        }
        b[j] = bi;
        R[bi] -= w[j];
    }
    return b;
}

long long simulate_and_error(const vector<int>& a, const vector<int>& b, long long L, const vector<int>& T) {
    int N = (int)a.size();
    vector<int> cnt(N, 0);
    int cur = 0;
    cnt[cur]++;
    for (long long w = 1; w < L; ++w) {
        int t = cnt[cur];
        int nxt = (t % 2 == 1) ? a[cur] : b[cur];
        cur = nxt;
        cnt[cur]++;
    }
    long long E = 0;
    for (int i = 0; i < N; ++i) {
        E += llabs((long long)cnt[i] - (long long)T[i]);
    }
    return E;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    long long L;
    if (!(cin >> N >> L)) {
        return 0;
    }
    vector<int> T(N);
    for (int i = 0; i < N; ++i) cin >> T[i];

    // Target probabilities
    vector<double> p(N);
    for (int i = 0; i < N; ++i) p[i] = (double)T[i] / (double)L;

    // Build ring order ascending by p
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int i, int j){
        if (p[i] != p[j]) return p[i] < p[j];
        return i < j;
    });

    // a edges form a ring
    vector<int> a(N), b(N);
    for (int k = 0; k < N; ++k) {
        int i = order[k];
        int j = order[(k + 1) % N];
        a[i] = j;
    }
    // prev mapping on ring
    vector<int> prev_of(N);
    for (int i = 0; i < N; ++i) prev_of[a[i]] = i;

    // Initial b assignment using p as weights
    vector<double> w0 = p;
    vector<double> S0(N);
    for (int i = 0; i < N; ++i) {
        S0[i] = 2.0 * p[i] - p[prev_of[i]];
    }
    b = assign_b_by_greedy(w0, S0);

    // Iteratively refine b using current stationary distribution
    int iterMax = 50;
    for (int it = 0; it < iterMax; ++it) {
        vector<double> v = compute_stationary(a, b);
        // Recompute S using current v
        vector<double> S(N);
        for (int i = 0; i < N; ++i) {
            S[i] = 2.0 * p[i] - v[prev_of[i]];
        }
        vector<int> b2 = assign_b_by_greedy(v, S);
        if (b2 == b) break;
        b.swap(b2);
    }

    // Evaluate error for this mapping by simulation
    long long err_iter = simulate_and_error(a, b, L, T);
    vector<int> best_a = a, best_b = b;
    long long best_err = err_iter;

    // Also evaluate a "uniform cycle" plan over best K (including employee 0)
    // Precompute prefix sums not needed. We'll compute error analytically.
    // For each K, select S as {0} + top K-1 by T (descending). Order them to give +1 counts to best candidates.
    vector<int> idx_desc(N);
    iota(idx_desc.begin(), idx_desc.end(), 0);
    sort(idx_desc.begin(), idx_desc.end(), [&](int i, int j){
        if (T[i] != T[j]) return T[i] > T[j];
        return i < j;
    });

    // Precompute total sum of T for speed
    long long sumT = 0;
    for (int i = 0; i < N; ++i) sumT += T[i];

    for (int K = 1; K <= N; ++K) {
        // Build S: include 0 and top K-1 others excluding 0
        vector<int> Sset;
        Sset.reserve(K);
        Sset.push_back(0);
        for (int t = 0, added = 0; t < N && added < K - 1; ++t) {
            int id = idx_desc[t];
            if (id == 0) continue;
            Sset.push_back(id);
            ++added;
        }
        if ((int)Sset.size() < K) continue;

        long long C = L / K;
        int r = (int)(L % K);

        // Base error: assuming all K nodes get C counts
        long long base_err = 0;
        long long sum_in_S = 0;
        for (int i : Sset) {
            base_err += llabs((long long)T[i] - C);
            sum_in_S += T[i];
        }
        // Others get 0 counts: contribute their T[i]
        long long err = base_err + (sumT - sum_in_S);

        // Adjust for +1 counts given to first r nodes on cycle: 0 must be among them if r>0
        long long delta = 0;
        if (r > 0) {
            // Node 0 gets +1
            if (T[0] >= C + 1) delta -= 1;
            else delta += 1;

            // For remaining r-1, choose from Sset\{0} those with T >= C+1 as many as possible
            int cnt_ge = 0;
            for (int i = 1; i < (int)Sset.size(); ++i) {
                if (T[Sset[i]] >= C + 1) cnt_ge++;
            }
            int take = min(cnt_ge, r - 1);
            delta += ( (r - 1) - 2LL * take );
        }
        err += delta;

        if (err < best_err) {
            best_err = err;
            // Build mapping: a_i=b_i forming cycle with desired +1 allocations: place 0 first,
            // then (r-1) highest T >= C+1 (excluding 0), then the rest.
            vector<int> hi, lo;
            for (int i = 1; i < (int)Sset.size(); ++i) {
                if (T[Sset[i]] >= C + 1) hi.push_back(Sset[i]);
                else lo.push_back(Sset[i]);
            }
            // Sort hi and lo by T descending for determinism
            sort(hi.begin(), hi.end(), [&](int x, int y){
                if (T[x] != T[y]) return T[x] > T[y];
                return x < y;
            });
            sort(lo.begin(), lo.end(), [&](int x, int y){
                if (T[x] != T[y]) return T[x] > T[y];
                return x < y;
            });
            vector<int> cycle;
            cycle.push_back(0);
            int need = max(0, r - 1);
            for (int i = 0; i < (int)hi.size() && need > 0; ++i) {
                cycle.push_back(hi[i]);
                need--;
                hi[i] = -1;
            }
            for (int i = 0; i < (int)hi.size(); ++i) if (hi[i] != -1) cycle.push_back(hi[i]);
            for (int x : lo) cycle.push_back(x);
            // ensure size K
            if ((int)cycle.size() > K) cycle.resize(K);

            vector<int> a2(N, 0), b2(N, 0);
            // link cycle
            for (int i = 0; i < (int)cycle.size(); ++i) {
                int u = cycle[i];
                int v = cycle[(i + 1) % (int)cycle.size()];
                a2[u] = v;
                b2[u] = v;
            }
            // non-cycle nodes point to 0
            for (int i = 0; i < N; ++i) {
                bool inS = false;
                // For speed we can use a mark
                // But K<=100, N<=100: O(NK) acceptable
                for (int u : cycle) if (u == i) { inS = true; break; }
                if (!inS) {
                    a2[i] = 0;
                    b2[i] = 0;
                }
            }
            best_a.swap(a2);
            best_b.swap(b2);
        }
    }

    // Output best mapping
    for (int i = 0; i < N; ++i) {
        cout << best_a[i] << ' ' << best_b[i] << '\n';
    }
    return 0;
}