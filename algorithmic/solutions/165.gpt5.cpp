#include <bits/stdc++.h>
using namespace std;

struct Pos {
    int i, j;
};

inline int manhattan(const Pos &a, const Pos &b) {
    return abs(a.i - b.i) + abs(a.j - b.j);
}

struct PathResult {
    int cost;
    vector<Pos> path;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    int si, sj;
    cin >> si >> sj;
    vector<string> A(N);
    for (int i = 0; i < N; ++i) cin >> A[i];
    vector<string> t(M);
    for (int k = 0; k < M; ++k) cin >> t[k];

    // Precompute positions of each letter
    vector<vector<Pos>> posList(26);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            posList[A[i][j] - 'A'].push_back(Pos{i, j});
        }
    }

    auto computeMinDistToLetter = [&](const Pos &cur, int letter) -> int {
        int best = INT_MAX;
        const auto &vec = posList[letter];
        for (const auto &p : vec) {
            int d = abs(cur.i - p.i) + abs(cur.j - p.j);
            if (d < best) best = d;
        }
        return best;
    };

    auto computeDP = [&](const Pos &cur, const string &w, bool needPath) -> PathResult {
        const vector<Pos>* lists[5];
        for (int s = 0; s < 5; ++s) {
            lists[s] = &posList[w[s] - 'A'];
        }
        const int INF = 1e9;
        vector<vector<int>> parent(5);
        vector<int> dpPrev(lists[0]->size(), INF);
        parent[0].assign(lists[0]->size(), -1);

        for (int k = 0; k < (int)lists[0]->size(); ++k) {
            dpPrev[k] = manhattan(cur, (*lists[0])[k]) + 1;
        }

        for (int s = 1; s < 5; ++s) {
            vector<int> dpNow(lists[s]->size(), INF);
            parent[s].assign(lists[s]->size(), -1);
            for (int k = 0; k < (int)lists[s]->size(); ++k) {
                const Pos &q = (*lists[s])[k];
                int bestCost = INF;
                int bestPar = -1;
                for (int p = 0; p < (int)lists[s-1]->size(); ++p) {
                    int c = dpPrev[p] + manhattan((*lists[s-1])[p], q) + 1;
                    if (c < bestCost) {
                        bestCost = c;
                        bestPar = p;
                    }
                }
                dpNow[k] = bestCost;
                parent[s][k] = bestPar;
            }
            dpPrev.swap(dpNow);
        }

        int lastIdx = -1;
        int bestCost = INF;
        for (int k = 0; k < (int)lists[4]->size(); ++k) {
            if (dpPrev[k] < bestCost) {
                bestCost = dpPrev[k];
                lastIdx = k;
            }
        }

        PathResult res;
        res.cost = bestCost;
        if (needPath) {
            vector<int> idxs(5);
            idxs[4] = lastIdx;
            for (int s = 4; s >= 1; --s) {
                idxs[s-1] = parent[s][idxs[s]];
            }
            res.path.resize(5);
            for (int s = 0; s < 5; ++s) {
                res.path[s] = (*lists[s])[idxs[s]];
            }
        }
        return res;
    };

    const int TOPK = 20;
    vector<char> used(M, 0);
    int remaining = M;
    Pos cur{si, sj};
    vector<pair<int,int>> outputs;
    outputs.reserve(M * 5);

    while (remaining > 0) {
        vector<pair<int,int>> cand; // (minDist, idx)
        cand.reserve(remaining);
        for (int k = 0; k < M; ++k) if (!used[k]) {
            int letter = t[k][0] - 'A';
            int d = computeMinDistToLetter(cur, letter);
            cand.emplace_back(d, k);
        }
        int K = min((int)cand.size(), TOPK);
        partial_sort(cand.begin(), cand.begin() + K, cand.end());
        int bestIdx = cand[0].second;
        int bestCost = INT_MAX;
        vector<Pos> bestPath;

        for (int z = 0; z < K; ++z) {
            int idx = cand[z].second;
            PathResult pr = computeDP(cur, t[idx], true);
            if (pr.cost < bestCost) {
                bestCost = pr.cost;
                bestIdx = idx;
                bestPath = move(pr.path);
            }
        }

        // Apply chosen path
        for (const auto &p : bestPath) {
            outputs.emplace_back(p.i, p.j);
        }
        cur = bestPath.back();
        used[bestIdx] = 1;
        --remaining;
    }

    for (auto &op : outputs) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}