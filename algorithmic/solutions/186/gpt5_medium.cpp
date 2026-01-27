#include <bits/stdc++.h>
using namespace std;

const int MAXC = 512;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<vector<unsigned char>> mat(N, vector<unsigned char>(N, 0));
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (!mat[u][v]) {
            mat[u][v] = mat[v][u] = 1;
        }
    }
    vector<vector<int>> adj(N);
    for (int i = 0; i < N; ++i) {
        adj[i].reserve(N);
        for (int j = 0; j < N; ++j) if (mat[i][j]) adj[i].push_back(j);
    }
    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = (int)adj[i].size();

    mt19937 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto dsatur_run = [&](vector<int>& outColor, int cap, mt19937& rng)->bool {
        outColor.assign(N, 0);
        vector<int> sat(N, 0);
        vector< bitset<MAXC> > pres(N);
        vector<char> uncolored(N, 1);
        int coloredCount = 0;
        int currentMaxColor = 0;

        while (coloredCount < N) {
            int bestSat = -1, bestDeg = -1;
            for (int i = 0; i < N; ++i) if (uncolored[i]) {
                if (sat[i] > bestSat) { bestSat = sat[i]; bestDeg = deg[i]; }
                else if (sat[i] == bestSat && deg[i] > bestDeg) { bestDeg = deg[i]; }
            }
            vector<int> cand;
            cand.reserve(N);
            for (int i = 0; i < N; ++i) if (uncolored[i] && sat[i] == bestSat && deg[i] == bestDeg) cand.push_back(i);
            int u = cand[rng() % cand.size()];

            int maxTry = cap ? cap : (MAXC - 1);
            int c = 1;
            while (c <= maxTry && pres[u].test(c)) ++c;
            if (c > maxTry) {
                if (cap) return false;
                // In practice, this should not happen as MAXC > N and deg <= N-1
                // But safeguard: if exceeded, fail.
                return false;
            }

            outColor[u] = c;
            uncolored[u] = 0;
            ++coloredCount;
            if (c > currentMaxColor) currentMaxColor = c;

            for (int w : adj[u]) if (uncolored[w]) {
                if (!pres[w].test(c)) {
                    pres[w].set(c);
                    ++sat[w];
                }
            }
        }
        return true;
    };

    auto coloring_max_color = [&](const vector<int>& col)->int {
        int K = 0;
        for (int c : col) if (c > K) K = c;
        return K;
    };

    auto reduce_by_local = [&](vector<int>& col, int& K, mt19937& rng)->bool {
        bool reduced = false;
        while (true) {
            vector<int> idx;
            idx.reserve(N);
            for (int i = 0; i < N; ++i) if (col[i] == K) idx.push_back(i);
            if (idx.empty()) { K--; reduced = true; break; }
            shuffle(idx.begin(), idx.end(), rng);
            bool changed = false;
            for (int v : idx) {
                vector<char> forbid(K, 0);
                for (int nb : adj[v]) {
                    int c = col[nb];
                    if (c >= 1 && c <= K - 1) forbid[c] = 1;
                }
                for (int c = 1; c <= K - 1; ++c) {
                    if (!forbid[c]) { col[v] = c; changed = true; break; }
                }
            }
            if (!changed) break;
        }
        return reduced;
    };

    auto start = chrono::high_resolution_clock::now();
    const long long totalBudgetMs = 1850; // keep some margin under 2s
    auto timePassedMs = [&]() -> long long {
        return chrono::duration_cast<chrono::milliseconds>(chrono::high_resolution_clock::now() - start).count();
    };

    vector<int> bestColor(N, 1), tmpColor;
    dsatur_run(bestColor, 0, rng);
    int bestK = coloring_max_color(bestColor);

    // Stage 1: multiple randomized DSatur runs (unlimited colors)
    while (timePassedMs() < totalBudgetMs * 6 / 10) {
        if (!dsatur_run(tmpColor, 0, rng)) continue;
        int K = coloring_max_color(tmpColor);
        if (K < bestK) { bestK = K; bestColor = tmpColor; }
    }

    // Quick local reduction attempts
    reduce_by_local(bestColor, bestK, rng);

    // Stage 2: try to find coloring with fewer colors using cap (DSatur with cap)
    for (int cap = bestK - 1; cap >= 1; --cap) {
        bool found = false;
        while (timePassedMs() < totalBudgetMs) {
            if (dsatur_run(tmpColor, cap, rng)) {
                bestColor = tmpColor;
                bestK = cap;
                found = true;
                // try local reduction again
                reduce_by_local(bestColor, bestK, rng);
                break;
            }
            // limit the number of attempts per cap implicitly by time
        }
        if (!found) break;
    }

    // Final safety: ensure valid and output
    // If invalid (shouldn't happen), fallback to greedy simple coloring
    auto is_valid = [&](const vector<int>& col)->bool {
        for (int u = 0; u < N; ++u) {
            if (col[u] < 1) return false;
            for (int v : adj[u]) {
                if (col[u] == col[v]) return false;
            }
        }
        return true;
    };
    if (!is_valid(bestColor)) {
        // fallback: simple greedy by degree order
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a, int b){ return deg[a] > deg[b]; });
        vector<int> col(N, 0);
        for (int u : order) {
            vector<char> forbid(N + 2, 0);
            for (int v : adj[u]) if (col[v] > 0) forbid[col[v]] = 1;
            int c = 1; while (c <= N && forbid[c]) ++c;
            if (c > N) c = 1;
            col[u] = c;
        }
        bestColor = col;
    }

    for (int i = 0; i < N; ++i) {
        cout << bestColor[i] << "\n";
    }
    return 0;
}