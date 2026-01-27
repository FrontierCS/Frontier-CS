#include <bits/stdc++.h>
using namespace std;

struct MaxClique {
    int N, M;
    int W;
    vector<vector<unsigned long long>> adj;
    vector<int> deg;
    vector<int> bestClique;
    chrono::steady_clock::time_point startTime;
    double timeLimit;
    bool timedOut = false;
    mt19937_64 rng;

    MaxClique(int n, int m): N(n), M(m) {
        W = (N + 63) >> 6;
        adj.assign(N, vector<unsigned long long>(W, 0));
        deg.assign(N, 0);
        rng.seed(chrono::steady_clock::now().time_since_epoch().count());
    }

    inline void setEdge(int u, int v) {
        int wu = v >> 6, bu = v & 63;
        int wv = u >> 6, bv = u & 63;
        adj[u][wu] |= (1ULL << bu);
        adj[v][wv] |= (1ULL << bv);
    }

    inline bool timeExceeded() {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - startTime).count();
        return elapsed >= timeLimit;
    }

    inline bool any(const vector<unsigned long long>& A) const {
        for (int i = 0; i < W; ++i) if (A[i]) return true;
        return false;
    }

    inline int bitsetCount(const vector<unsigned long long>& A) const {
        int c = 0;
        for (int i = 0; i < W; ++i) c += __builtin_popcountll(A[i]);
        return c;
    }

    inline void setFull(vector<unsigned long long>& A) const {
        for (int i = 0; i < W; ++i) A[i] = ~0ULL;
        int rem = N & 63;
        if (rem) A[W-1] = (rem == 0) ? ~0ULL : ((1ULL << rem) - 1);
    }

    inline void clearBit(vector<unsigned long long>& A, int idx) const {
        A[idx >> 6] &= ~(1ULL << (idx & 63));
    }

    inline int popFirst(vector<unsigned long long>& A) const {
        for (int i = 0; i < W; ++i) {
            unsigned long long x = A[i];
            if (x) {
                int b = __builtin_ctzll(x);
                A[i] = x & (x - 1);
                return (i << 6) + b;
            }
        }
        return -1;
    }

    inline int firstSet(const vector<unsigned long long>& A) const {
        for (int i = 0; i < W; ++i) {
            unsigned long long x = A[i];
            if (x) {
                int b = __builtin_ctzll(x);
                return (i << 6) + b;
            }
        }
        return -1;
    }

    inline void and_inplace(vector<unsigned long long>& A, const vector<unsigned long long>& B) const {
        for (int i = 0; i < W; ++i) A[i] &= B[i];
    }

    inline void andnot_inplace(vector<unsigned long long>& A, const vector<unsigned long long>& B) const {
        for (int i = 0; i < W; ++i) A[i] &= ~B[i];
    }

    inline int countCommon(const vector<unsigned long long>& A, int v) const {
        int cnt = 0;
        const auto &row = adj[v];
        for (int i = 0; i < W; ++i) cnt += __builtin_popcountll(A[i] & row[i]);
        return cnt;
    }

    vector<int> greedyClique() {
        vector<unsigned long long> cand(W);
        setFull(cand);
        vector<int> clique;
        while (any(cand)) {
            int bestv = -1, bestscore = -1, bestdeg = -1;
            for (int wi = 0; wi < W; ++wi) {
                unsigned long long mask = cand[wi];
                while (mask) {
                    int b = __builtin_ctzll(mask);
                    int v = (wi << 6) + b;
                    if (v >= N) break;
                    int score = countCommon(cand, v);
                    if (score > bestscore || (score == bestscore && (deg[v] > bestdeg || (deg[v] == bestdeg && (rng() & 1))))) {
                        bestscore = score;
                        bestv = v;
                        bestdeg = deg[v];
                    }
                    mask &= (mask - 1);
                }
            }
            if (bestv == -1) break;
            clique.push_back(bestv);
            and_inplace(cand, adj[bestv]);
        }
        return clique;
    }

    vector<int> greedyFromBase(const vector<int>& base, int skip = -1) {
        vector<unsigned long long> cand(W);
        setFull(cand);
        for (int v : base) {
            if (v == skip) continue;
            and_inplace(cand, adj[v]);
        }
        vector<int> clique;
        for (int v : base) if (v != skip) clique.push_back(v);
        while (any(cand)) {
            int bestv = -1, bestscore = -1, bestdeg = -1;
            for (int wi = 0; wi < W; ++wi) {
                unsigned long long mask = cand[wi];
                while (mask) {
                    int b = __builtin_ctzll(mask);
                    int v = (wi << 6) + b;
                    if (v >= N) break;
                    int score = countCommon(cand, v);
                    if (score > bestscore || (score == bestscore && (deg[v] > bestdeg || (deg[v] == bestdeg && (rng() & 1))))) {
                        bestscore = score;
                        bestv = v;
                        bestdeg = deg[v];
                    }
                    mask &= (mask - 1);
                }
            }
            if (bestv == -1) break;
            clique.push_back(bestv);
            and_inplace(cand, adj[bestv]);
        }
        return clique;
    }

    void colorSort(const vector<unsigned long long>& P, vector<int>& order, vector<int>& colors) const {
        order.clear(); colors.clear();
        vector<unsigned long long> Ptmp = P;
        int color = 0;
        while (any(Ptmp)) {
            ++color;
            vector<unsigned long long> Q = Ptmp;
            while (any(Q)) {
                int v = popFirst(Q);
                order.push_back(v);
                colors.push_back(color);
                andnot_inplace(Q, adj[v]);
                clearBit(Ptmp, v);
            }
        }
    }

    void expand(vector<unsigned long long> P, vector<int>& R) {
        if (timedOut || timeExceeded()) { timedOut = true; return; }
        if (!any(P)) {
            if ((int)R.size() > (int)bestClique.size()) bestClique = R;
            return;
        }
        vector<int> order; order.reserve(64);
        vector<int> colors; colors.reserve(64);
        colorSort(P, order, colors);
        while (!order.empty()) {
            if ((int)R.size() + colors.back() <= (int)bestClique.size()) return;
            int v = order.back(); order.pop_back(); colors.pop_back();
            vector<unsigned long long> P2 = P;
            and_inplace(P2, adj[v]);
            R.push_back(v);
            expand(P2, R);
            R.pop_back();
            if (timedOut) return;
        }
    }

    void solve() {
        startTime = chrono::steady_clock::now();
        timeLimit = 1.95; // total time budget
        // compute degrees
        for (int i = 0; i < N; ++i) {
            int c = 0;
            for (int j = 0; j < W; ++j) c += __builtin_popcountll(adj[i][j]);
            deg[i] = c;
        }

        // Greedy multistart phase
        double greedyBudget = 0.35;
        int attempts = 0;
        while (true) {
            if (timeExceeded() || chrono::duration<double>(chrono::steady_clock::now() - startTime).count() >= greedyBudget) break;
            vector<int> clq = greedyClique();
            if ((int)clq.size() > (int)bestClique.size()) bestClique = clq;
            attempts++;
            if (attempts > 50) break;
        }

        // Local improvement by drop-one-and-extend
        if (!bestClique.empty()) {
            int K = (int)bestClique.size();
            int trials = min(K, 25);
            for (int t = 0; t < trials; ++t) {
                if (timeExceeded()) break;
                int idx = t % K;
                vector<int> clq = greedyFromBase(bestClique, bestClique[idx]);
                if ((int)clq.size() > (int)bestClique.size()) {
                    bestClique = clq;
                    K = (int)bestClique.size();
                }
            }
        }

        // Branch and Bound with coloring (time-limited)
        double elapsed = chrono::duration<double>(chrono::steady_clock::now() - startTime).count();
        if (elapsed < timeLimit - 0.05) {
            vector<unsigned long long> P(W);
            setFull(P);
            vector<int> R;
            expand(P, R);
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    MaxClique solver(N, M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        solver.setEdge(u, v);
        solver.setEdge(v, u);
    }

    solver.solve();

    vector<int> inClique(N, 0);
    for (int v : solver.bestClique) if (v >= 0 && v < N) inClique[v] = 1;

    for (int i = 0; i < N; ++i) {
        cout << inClique[i] << '\n';
    }
    return 0;
}