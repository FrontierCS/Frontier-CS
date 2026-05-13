#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // ---- Read input ----
    int n = inf.readInt();
    int m = inf.readInt();
    int t = inf.readInt();
    int k = inf.readInt();

    vector<long long> a(n + 1);
    for (int i = 1; i <= n; i++) a[i] = (long long)inf.readLong() % m;

    vector<long long> c(n + 1);
    for (int i = 1; i <= n; i++) c[i] = inf.readLong();

    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; i++) {
        int u = inf.readInt(), v = inf.readInt();
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<int> sv(t);
    vector<long long> wv(t);
    for (int j = 0; j < t; j++) {
        sv[j] = inf.readInt();
        wv[j] = inf.readLong();
    }

    // ---- Root tree at 1 (BFS) ----
    vector<int> par(n + 1, 0);
    vector<int> bfs_order;
    bfs_order.reserve(n);
    vector<bool> visited(n + 1, false);
    {
        queue<int> q;
        q.push(1);
        visited[1] = true;
        par[1] = 0;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            bfs_order.push_back(u);
            for (int v : adj[u]) {
                if (!visited[v]) {
                    visited[v] = true;
                    par[v] = u;
                    q.push(v);
                }
            }
        }
    }

    // Build children list
    vector<vector<int>> children(n + 1);
    for (int i = 2; i <= n; i++)
        children[par[i]].push_back(i);

    // Euler tour (tin/tout), 0-indexed positions
    vector<int> tin(n + 1), tout(n + 1);
    vector<int> euler_pos(n + 1); // euler_pos[pos] = node
    {
        int timer = 0;
        stack<pair<int,bool>> stk;
        stk.push({1, false});
        while (!stk.empty()) {
            auto [u, leaving] = stk.top(); stk.pop();
            if (leaving) {
                tout[u] = timer - 1;
            } else {
                tin[u] = timer;
                euler_pos[timer] = u;
                timer++;
                stk.push({u, true});
                for (int i = (int)children[u].size() - 1; i >= 0; i--)
                    stk.push({children[u][i], false});
            }
        }
    }

    // ---- Precompute primes in [2, m) ----
    vector<int> primes;
    {
        vector<bool> sieve(m, true);
        for (int p = 2; p < m; p++) {
            if (!sieve[p]) continue;
            primes.push_back(p);
            for (int q = 2*p; q < m; q += p) sieve[q] = false;
        }
    }
    int P_size = (int)primes.size();
    // Map residue -> prime index (-1 if not prime)
    vector<int> prime_idx(m, -1);
    for (int i = 0; i < P_size; i++) prime_idx[primes[i]] = i;

    // ---- Helper: given cumulative shifts, compute F ----
    // cumshift[v] = total shift added to node v (sum of x on path from root to v)
    auto compute_objective = [&](const vector<long long>& cumshift, long long retuner_cost) -> long long {
        // Final residues in euler order
        // Build prefix count for each prime over euler positions [0..n-1]
        // prefix[p][pos] = number of nodes with residue primes[p] in euler positions [0..pos)
        vector<vector<int>> prefix(P_size, vector<int>(n + 1, 0));
        for (int pos = 0; pos < n; pos++) {
            int u = euler_pos[pos];
            int r = (int)((a[u] + cumshift[u]) % m);
            for (int pi = 0; pi < P_size; pi++) prefix[pi][pos + 1] = prefix[pi][pos];
            if (prime_idx[r] >= 0) {
                int pi = prime_idx[r];
                prefix[pi][pos + 1]++;
            }
        }

        long long total_penalty = 0;
        for (int j = 0; j < t; j++) {
            int sj = sv[j];
            int lo = tin[sj], hi = tout[sj]; // inclusive positions
            int covered = 0;
            for (int pi = 0; pi < P_size; pi++) {
                int cnt = prefix[pi][hi + 1] - prefix[pi][lo];
                if (cnt > 0) covered++;
            }
            total_penalty += wv[j] * (long long)(P_size - covered);
        }
        return total_penalty + retuner_cost;
    };

    // ---- Compute F_base (no retuners) ----
    vector<long long> zero_shift(n + 1, 0LL);
    long long F_base = compute_objective(zero_shift, 0LL);

    // ---- Read participant output ----
    int q = ouf.readInt(0, n, "number of retuners q");
    if (q > k) {
        quitf(_wa, "q=%d exceeds k=%d", q, k);
    }

    vector<pair<int,int>> retuners(q);
    set<int> used_nodes;
    long long retuner_cost = 0;

    for (int i = 0; i < q; i++) {
        int v = ouf.readInt(1, n, "retuner node v");
        int d = ouf.readInt(1, m - 1, "retuner shift d");
        if (used_nodes.count(v)) {
            quitf(_wa, "node %d appears more than once in retuner list", v);
        }
        used_nodes.insert(v);
        retuners[i] = {v, d};
        retuner_cost += c[v];
    }

    // Check EOF
    if (!ouf.seekEof()) {
        quitf(_wa, "extra data after the last retuner");
    }

    // ---- Build cumulative shifts ----
    // x[v] = shift placed at v (0 if none)
    vector<long long> x(n + 1, 0LL);
    for (auto [v, d] : retuners) x[v] = d;

    // Propagate: cumshift[u] = cumshift[par[u]] + x[u], in BFS order
    vector<long long> cumshift(n + 1, 0LL);
    for (int u : bfs_order) {
        if (par[u] == 0)
            cumshift[u] = x[u] % m;
        else
            cumshift[u] = (cumshift[par[u]] + x[u]) % m;
    }

    // ---- Compute F ----
    long long F = compute_objective(cumshift, retuner_cost);

    // ---- Score ----
    double score_ratio;
    if (F_base == 0) {
        if (F == 0) {
            score_ratio = 1.0;
        } else {
            // Feasible but F>0 when F_base=0 means participant made things worse somehow
            // Actually per statement: if F_base=0 and F!=0, score=0
            score_ratio = 0.0;
        }
    } else {
        double improvement = (double)(F_base - F) / (double)F_base;
        score_ratio = max(0.0, improvement);
        if (score_ratio > 1.0) score_ratio = 1.0;
    }

    long long int_score = (long long)floor(1000000.0 * score_ratio);

    quitp(score_ratio,
          "F_base=%lld F=%lld retuner_cost=%lld q=%d score=%lld Ratio: %.6f",
          F_base, F, retuner_cost, q, int_score, score_ratio);

    return 0;
}