#include <bits/stdc++.h>
using namespace std;

struct Pos {
    int r, c;
};

int manhattan(const Pos &a, const Pos &b) {
    return abs(a.r - b.r) + abs(a.c - b.c);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    int si, sj;
    cin >> si >> sj;
    vector<string> grid(N);
    for (int i = 0; i < N; ++i) cin >> grid[i];
    vector<string> words(M);
    for (int k = 0; k < M; ++k) cin >> words[k];
    
    // Precompute positions for each letter
    vector<vector<Pos>> occ(26);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            occ[grid[i][j] - 'A'].push_back({i, j});
        }
    }
    
    auto compute_min_cost = [&](const Pos &start, const string &w) -> int {
        const vector<Pos> *V[5];
        for (int t = 0; t < 5; ++t) V[t] = &occ[w[t] - 'A'];
        // DP
        const int INF = 1e9;
        vector<int> dp_prev(V[0]->size(), INF);
        for (size_t j = 0; j < V[0]->size(); ++j) {
            dp_prev[j] = manhattan(start, (*V[0])[j]) + 1;
        }
        for (int t = 1; t < 5; ++t) {
            vector<int> dp_cur(V[t]->size(), INF);
            for (size_t j = 0; j < V[t]->size(); ++j) {
                int best = INF;
                const Pos &to = (*V[t])[j];
                for (size_t i = 0; i < V[t-1]->size(); ++i) {
                    int cand = dp_prev[i] + manhattan((*V[t-1])[i], to) + 1;
                    if (cand < best) best = cand;
                }
                dp_cur[j] = best;
            }
            dp_prev.swap(dp_cur);
        }
        int best = INF;
        for (size_t j = 0; j < dp_prev.size(); ++j) best = min(best, dp_prev[j]);
        return best;
    };
    
    auto compute_path = [&](const Pos &start, const string &w) -> vector<Pos> {
        const vector<Pos> *V[5];
        for (int t = 0; t < 5; ++t) V[t] = &occ[w[t] - 'A'];
        const int INF = 1e9;
        vector<int> dp0(V[0]->size(), INF);
        vector<vector<int>> parent(5);
        parent[0] = vector<int>(V[0]->size(), -1);
        for (size_t j = 0; j < V[0]->size(); ++j) {
            dp0[j] = manhattan(start, (*V[0])[j]) + 1;
        }
        vector<int> dp_prev = dp0;
        for (int t = 1; t < 5; ++t) {
            vector<int> dp_cur(V[t]->size(), INF);
            parent[t] = vector<int>(V[t]->size(), -1);
            for (size_t j = 0; j < V[t]->size(); ++j) {
                int best = INF;
                int best_i = -1;
                const Pos &to = (*V[t])[j];
                for (size_t i = 0; i < V[t-1]->size(); ++i) {
                    int cand = dp_prev[i] + manhattan((*V[t-1])[i], to) + 1;
                    if (cand < best) {
                        best = cand;
                        best_i = (int)i;
                    }
                }
                dp_cur[j] = best;
                parent[t][j] = best_i;
            }
            dp_prev.swap(dp_cur);
        }
        // Find best end
        int end_idx = -1;
        int best = 1e9;
        for (size_t j = 0; j < dp_prev.size(); ++j) {
            if (dp_prev[j] < best) {
                best = dp_prev[j];
                end_idx = (int)j;
            }
        }
        // Reconstruct
        vector<Pos> path(5);
        int idx = end_idx;
        for (int t = 4; t >= 0; --t) {
            path[t] = (*V[t])[idx];
            if (t > 0) idx = parent[t][idx];
        }
        return path;
    };
    
    Pos cur{si, sj};
    vector<int> remaining(M);
    iota(remaining.begin(), remaining.end(), 0);
    
    // Greedy: always pick the next word with minimal cost from current position
    while (!remaining.empty()) {
        int best_idx_in_remaining = -1;
        int best_cost = INT_MAX;
        for (int i = 0; i < (int)remaining.size(); ++i) {
            int idx = remaining[i];
            int cost = compute_min_cost(cur, words[idx]);
            if (cost < best_cost) {
                best_cost = cost;
                best_idx_in_remaining = i;
            }
        }
        int word_idx = remaining[best_idx_in_remaining];
        vector<Pos> path = compute_path(cur, words[word_idx]);
        for (auto &p : path) {
            cout << p.r << ' ' << p.c << '\n';
            cur = p;
        }
        remaining.erase(remaining.begin() + best_idx_in_remaining);
    }
    
    return 0;
}