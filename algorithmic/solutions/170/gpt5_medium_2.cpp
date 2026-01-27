#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    long long L;
    if (!(cin >> N >> L)) return 0;
    vector<int> T(N);
    for (int i = 0; i < N; ++i) cin >> T[i];

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Initialize a_i as ring to ensure strong connectivity
    vector<int> a(N), b(N);
    for (int i = 0; i < N; ++i) a[i] = (i + 1) % N;

    // Target for b edges given a is ring:
    // We want sum_i m_{i->j} T_i ≈ 2*T_j.
    // With a fixed ring a_i = j for i = j-1, a contributes T_{j-1}.
    // So desired b contribution for j is S_j = 2*T_j - T_{j-1}.
    vector<long long> S(N);
    for (int j = 0; j < N; ++j) {
        int jm1 = (j - 1 + N) % N;
        S[j] = 2LL * T[j] - T[jm1];
    }

    // Assign b using greedy to match S as closely as possible with items of weights T_i
    // Each i contributes once (one b edge).
    // Use a max-heap of remaining capacities S.
    struct Node { long long rem; int j; };
    struct Cmp { bool operator()(const Node& x, const Node& y) const { return x.rem < y.rem; } }; // max-heap
    priority_queue<Node, vector<Node>, Cmp> pq;
    for (int j = 0; j < N; ++j) pq.push({S[j], j});

    // Sort sources by descending T_i
    vector<int> idx(N);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int i, int j){ return T[i] > T[j]; });

    for (int k = 0; k < N; ++k) {
        int i = idx[k];
        Node top = pq.top(); pq.pop();
        int j = top.j;
        b[i] = j;
        top.rem -= T[i];
        pq.push(top);
    }

    // Optional small local improvement using approximate stationary distribution
    auto compute_pi = [&](const vector<int>& aa, const vector<int>& bb, const vector<double>& init, int iters, double alpha){
        int n = aa.size();
        vector<double> v = init;
        if (v.empty()) {
            v.assign(n, 1.0 / n);
        } else {
            double s = 0;
            for (double x : v) s += x;
            if (s <= 0) {
                v.assign(n, 1.0 / n);
            } else {
                for (double &x : v) x /= s;
            }
        }
        vector<double> u(n, 0.0);
        for (int it = 0; it < iters; ++it) {
            fill(u.begin(), u.end(), 0.0);
            for (int i = 0; i < n; ++i) {
                double val = 0.5 * v[i];
                u[aa[i]] += val;
                u[bb[i]] += val;
            }
            for (int j = 0; j < n; ++j) v[j] = alpha * v[j] + (1.0 - alpha) * u[j];
        }
        double s = 0;
        for (double x : v) s += x;
        if (s > 0) for (double &x : v) x /= s;
        else for (double &x : v) x = 1.0 / n;
        return v;
    };
    auto approx_error = [&](const vector<double>& pi){
        long long E = 0;
        for (int i = 0; i < N; ++i) {
            long long pred = (long long) llround(pi[i] * (double)L);
            E += llabs(pred - (long long)T[i]);
        }
        return E;
    };

    vector<double> init_pi(N);
    for (int i = 0; i < N; ++i) init_pi[i] = (double)T[i] / (double)L;
    vector<double> pi = compute_pi(a, b, init_pi, 800, 0.5);
    long long bestE = approx_error(pi);

    // Build deficits list
    auto build_deficits = [&](const vector<double>& pi){
        vector<pair<double,int>> pos;
        for (int i = 0; i < N; ++i) {
            double pred = pi[i] * (double)L;
            double d = (double)T[i] - pred;
            if (d > 0) pos.emplace_back(d, i);
        }
        sort(pos.begin(), pos.end(), [&](auto &x, auto &y){ return x.first > y.first; });
        vector<int> top;
        int K = min((int)pos.size(), 20);
        for (int k = 0; k < K; ++k) top.push_back(pos[k].second);
        return top;
    };
    vector<int> topPos = build_deficits(pi);

    // Weighted sampling over pi for choosing i
    auto build_prefix = [&](const vector<double>& pi){
        vector<double> pref(N);
        double acc = 0;
        for (int i = 0; i < N; ++i) {
            acc += max(pi[i], 1e-15);
            pref[i] = acc;
        }
        if (acc <= 0) {
            for (int i = 0; i < N; ++i) pref[i] = (i+1);
        }
        return pref;
    };
    vector<double> pref = build_prefix(pi);

    auto sample_i = [&](const vector<double>& pref)->int{
        double tot = pref.back();
        uniform_real_distribution<double> dist(0.0, tot);
        double r = dist(rng);
        int i = int(lower_bound(pref.begin(), pref.end(), r) - pref.begin());
        if (i >= (int)pref.size()) i = pref.size()-1;
        return i;
    };

    auto now = chrono::steady_clock::now();
    auto end_time = now + chrono::milliseconds(1700); // time budget

    // Local search attempts
    int attempts = 0;
    while (chrono::steady_clock::now() < end_time) {
        // periodic refine pi and helpers
        if (attempts % 50 == 0) {
            pi = compute_pi(a, b, pi, 300, 0.5);
            bestE = approx_error(pi);
            pref = build_prefix(pi);
            topPos = build_deficits(pi);
        }
        ++attempts;
        int i = sample_i(pref);
        int jcand;
        if (!topPos.empty() && uniform_int_distribution<int>(0, 9)(rng) < 7) {
            jcand = topPos[uniform_int_distribution<int>(0, (int)topPos.size()-1)(rng)];
        } else {
            jcand = uniform_int_distribution<int>(0, N-1)(rng);
        }
        if (jcand == b[i]) continue;

        int old_bi = b[i];
        b[i] = jcand;
        vector<double> pi2 = compute_pi(a, b, pi, 200, 0.5);
        long long E2 = approx_error(pi2);
        if (E2 < bestE) {
            bestE = E2;
            pi.swap(pi2);
            pref = build_prefix(pi);
            topPos = build_deficits(pi);
        } else {
            b[i] = old_bi;
        }
    }

    // Output
    for (int i = 0; i < N; ++i) {
        cout << a[i] << ' ' << b[i] << '\n';
    }
    return 0;
}