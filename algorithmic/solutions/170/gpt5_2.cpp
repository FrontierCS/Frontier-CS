#include <bits/stdc++.h>
using namespace std;

struct Plan {
    vector<int> a, b;
    long long objective; // sum |S - D|
};

static long long llabsll(long long x){ return x < 0 ? -x : x; }

Plan build_plan_with_ring(const vector<int>& ring_next, const vector<long long>& T, const vector<long long>& D) {
    int N = (int)T.size();
    vector<int> a(N), b(N, -1);
    vector<long long> S(N, 0);

    // Set a_i according to ring_next (permutation forming a single cycle)
    for (int i = 0; i < N; i++) {
        a[i] = ring_next[i];
        S[a[i]] += T[i];
    }

    // Greedy assignment for b_i to minimize sum |S - D|
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int i, int j){
        if (T[i] != T[j]) return T[i] > T[j];
        return i < j;
    });

    for (int idx = 0; idx < N; idx++) {
        int i = order[idx];
        long long w = T[i];
        int bestJ = 0;
        long long bestDelta = LLONG_MIN;
        long long bestNew = LLONG_MAX;
        for (int j = 0; j < N; j++) {
            long long cur = llabsll(S[j] - D[j]);
            long long neu = llabsll(S[j] + w - D[j]);
            long long delta = cur - neu;
            if (delta > bestDelta || (delta == bestDelta && neu < bestNew)) {
                bestDelta = delta;
                bestNew = neu;
                bestJ = j;
            }
        }
        b[i] = bestJ;
        S[bestJ] += w;
    }

    // 1-opt local improvement: move token of i from its bin to other bin if improves |S-D|
    bool improved = true;
    int iter = 0, maxIter = 5 * N; // limit iterations just in case
    while (improved && iter < maxIter) {
        improved = false;
        iter++;
        for (int i = 0; i < N; i++) {
            long long w = T[i];
            if (w == 0) {
                if (b[i] < 0) b[i] = a[i];
                continue;
            }
            int oldj = b[i];
            if (oldj < 0) oldj = a[i]; // fallback
            long long bestDelta = 0;
            int bestJ = oldj;
            long long cur_oldj = llabsll(S[oldj] - D[oldj]);
            for (int j = 0; j < N; j++) {
                if (j == oldj) continue;
                long long cur_j = llabsll(S[j] - D[j]);
                long long new_oldj = llabsll((S[oldj] - w) - D[oldj]);
                long long new_j = llabsll((S[j] + w) - D[j]);
                long long delta = (cur_oldj + cur_j) - (new_oldj + new_j);
                if (delta > bestDelta) {
                    bestDelta = delta;
                    bestJ = j;
                }
            }
            if (bestJ != oldj) {
                // apply move
                S[oldj] -= w;
                S[bestJ] += w;
                b[i] = bestJ;
                improved = true;
            } else {
                if (b[i] < 0) b[i] = a[i];
            }
        }
    }

    long long obj = 0;
    for (int j = 0; j < N; j++) obj += llabsll(S[j] - D[j]);

    Plan plan;
    plan.a = a;
    plan.b = b;
    plan.objective = obj;
    return plan;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    long long L;
    if(!(cin >> N >> L)) return 0;
    vector<long long> T(N);
    for (int i = 0; i < N; i++) cin >> T[i];
    vector<long long> D(N);
    for (int i = 0; i < N; i++) D[i] = 2 * T[i];

    // Build a permutation p by sorted pairing to minimize sum |T_i - 2*T_p(i)|
    vector<int> donors(N), recips(N);
    iota(donors.begin(), donors.end(), 0);
    iota(recips.begin(), recips.end(), 0);
    sort(donors.begin(), donors.end(), [&](int i, int j){
        if (T[i] != T[j]) return T[i] < T[j];
        return i < j;
    });
    sort(recips.begin(), recips.end(), [&](int i, int j){
        if (D[i] != D[j]) return D[i] < D[j];
        return i < j;
    });

    vector<int> p(N, -1); // mapping i -> j
    for (int k = 0; k < N; k++) {
        p[donors[k]] = recips[k];
    }

    // Merge cycles of permutation p into a single cycle by swapping edges with an anchor
    vector<int> vis(N, 0);
    vector<vector<int>> cycles;
    for (int i = 0; i < N; i++) if (!vis[i]) {
        int x = i;
        vector<int> cyc;
        while (!vis[x]) {
            vis[x] = 1;
            cyc.push_back(x);
            x = p[x];
        }
        cycles.push_back(cyc);
    }
    if ((int)cycles.size() > 1) {
        int anchor = cycles[0][0];
        for (int t = 1; t < (int)cycles.size(); t++) {
            int x = cycles[t][0];
            int v = p[anchor];
            int y = p[x];
            // swap p[anchor] and p[x]
            p[anchor] = y;
            p[x] = v;
        }
    }
    // Now p is a single cycle permutation for 'a' edges.

    // Candidate 1: ring from optimized p (single cycle)
    vector<int> ring1 = p;

    // Candidate 2: simple numeric ring i -> (i+1)%N
    vector<int> ring2(N);
    for (int i = 0; i < N; i++) ring2[i] = (i + 1) % N;

    Plan plan1 = build_plan_with_ring(ring1, T, D);
    Plan plan2 = build_plan_with_ring(ring2, T, D);

    Plan best = (plan1.objective <= plan2.objective ? plan1 : plan2);

    // Output
    for (int i = 0; i < N; i++) {
        cout << best.a[i] << " " << best.b[i] << "\n";
    }

    return 0;
}