#include <bits/stdc++.h>
using namespace std;

#ifdef _WIN32
#define getchar_unlocked getchar
#endif

static inline int fast_read() {
    int x = 0, c = getchar_unlocked();
    while (c < '0' || c > '9') {
        if (c == EOF) return -1;
        c = getchar_unlocked();
    }
    for (; c >= '0' && c <= '9'; c = getchar_unlocked()) x = x * 10 + (c - '0');
    return x;
}

const int MAXN = 10050;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N = fast_read();
    int M = fast_read();
    if (N <= 0) return 0;

    vector<vector<int>> g(N);
    g.reserve(N);

    for (int i = 0; i < M; ++i) {
        int u = fast_read();
        int v = fast_read();
        if (u <= 0 || v <= 0) continue;
        --u; --v;
        if (u == v) continue;
        g[u].push_back(v);
        g[v].push_back(u);
    }

    // Deduplicate adjacency lists
    for (int i = 0; i < N; ++i) {
        auto &adj = g[i];
        sort(adj.begin(), adj.end());
        adj.erase(unique(adj.begin(), adj.end()), adj.end());
    }

    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = (int)g[i].size();

    // Precompute neighbor degree sums for heuristic
    vector<int> nsum(N, 0);
    for (int i = 0; i < N; ++i) {
        int s = 0;
        for (int u : g[i]) s += deg[u];
        nsum[i] = s;
    }

    // Build bitset adjacency for quick adjacency checks in local search
    vector< bitset<MAXN> > adjBit;
    adjBit.resize(N);
    for (int i = 0; i < N; ++i) {
        for (int u : g[i]) {
            if (u >= 0 && u < MAXN) adjBit[i].set(u);
        }
    }

    auto start = chrono::steady_clock::now();
    double time_limit = 1.90; // seconds
    auto elapsed = [&]() -> double {
        auto now = chrono::steady_clock::now();
        return chrono::duration<double>(now - start).count();
    };

    std::mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    auto build_from_order = [&](const vector<int>& order, vector<char>& selected) -> int {
        selected.assign(N, 0);
        vector<char> banned(N, 0);
        int K = 0;
        for (int v : order) {
            if (!banned[v]) {
                selected[v] = 1;
                ++K;
                banned[v] = 1;
                for (int u : g[v]) banned[u] = 1;
            }
        }
        return K;
    };

    vector<char> bestSel(N, 0), curSel(N, 0);
    int bestK = 0;

    vector<int> order(N);
    iota(order.begin(), order.end(), 0);

    // Different ordering strategies
    int iter = 0;
    while (elapsed() < time_limit * 0.65) {
        int mode = iter % 5;
        if (mode == 0) {
            // degree ascending, tie by index
            sort(order.begin(), order.end(), [&](int a, int b){
                if (deg[a] != deg[b]) return deg[a] < deg[b];
                return a < b;
            });
        } else if (mode == 1) {
            // degree ascending with random tie-break
            vector<pair<pair<int, uint64_t>, int>> arr;
            arr.reserve(N);
            for (int i = 0; i < N; ++i) {
                arr.push_back({{deg[i], rng()}, i});
            }
            sort(arr.begin(), arr.end(), [&](const auto& A, const auto& B){
                if (A.first.first != B.first.first) return A.first.first < B.first.first;
                return A.first.second < B.first.second;
            });
            for (int i = 0; i < N; ++i) order[i] = arr[i].second;
        } else if (mode == 2) {
            // composite: (deg, neighbor sum)
            sort(order.begin(), order.end(), [&](int a, int b){
                if (deg[a] != deg[b]) return deg[a] < deg[b];
                if (nsum[a] != nsum[b]) return nsum[a] < nsum[b];
                return a < b;
            });
        } else if (mode == 3) {
            // random shuffle
            shuffle(order.begin(), order.end(), rng);
        } else {
            // degree descending (try sometimes)
            sort(order.begin(), order.end(), [&](int a, int b){
                if (deg[a] != deg[b]) return deg[a] > deg[b];
                return a < b;
            });
        }

        int K = build_from_order(order, curSel);
        if (K > bestK) {
            bestK = K;
            bestSel = curSel;
        }
        ++iter;
    }

    // Local improvement: 1-2 swaps with augmentation
    auto two_for_one_improve = [&](vector<char>& inSet, int& curK, double remain_fraction) {
        // conflict_count[u] = number of selected neighbors of u (assuming no multiedges)
        vector<int> conflict(N, 0);
        for (int v = 0; v < N; ++v) if (inSet[v]) {
            for (int u : g[v]) ++conflict[u];
        }

        auto augment_greedy = [&](){
            // Add all vertices with conflict 0
            for (int w = 0; w < N; ++w) {
                if (!inSet[w] && conflict[w] == 0) {
                    inSet[w] = 1;
                    ++curK;
                    for (int x : g[w]) ++conflict[x];
                }
            }
        };

        // The set should already be maximal; but after swaps it may not be; we'll re-augment
        vector<int> selList;
        selList.reserve(curK + 16);

        bool improved = true;
        int rounds = 0;
        while (improved && elapsed() < time_limit * remain_fraction) {
            improved = false;
            selList.clear();
            for (int v = 0; v < N; ++v) if (inSet[v]) selList.push_back(v);
            shuffle(selList.begin(), selList.end(), rng);

            for (int v : selList) {
                if (!inSet[v]) continue;
                vector<int> F;
                F.reserve(16);
                for (int u : g[v]) {
                    if (!inSet[u] && conflict[u] == 1) F.push_back(u);
                }
                if ((int)F.size() < 2) continue;

                int a = -1, b = -1;
                bool found = false;

                if ((int)F.size() <= 64) {
                    // Try all pairs
                    for (int i = 0; i < (int)F.size() && !found; ++i) {
                        for (int j = i + 1; j < (int)F.size(); ++j) {
                            int x = F[i], y = F[j];
                            if (!adjBit[x].test(y)) {
                                a = x; b = y; found = true; break;
                            }
                        }
                    }
                } else {
                    // Random sampling
                    int tries = 500;
                    for (int t = 0; t < tries && !found; ++t) {
                        int i = (int)(rng() % F.size());
                        int j = (int)(rng() % F.size());
                        if (i == j) continue;
                        int x = F[i], y = F[j];
                        if (!adjBit[x].test(y)) {
                            a = x; b = y; found = true; break;
                        }
                    }
                    if (!found) {
                        // Heuristic: try minimal-degree candidates
                        partial_sort(F.begin(), F.begin() + 16, F.end(), [&](int x, int y){
                            if (deg[x] != deg[y]) return deg[x] < deg[y];
                            return x < y;
                        });
                        int L = min(16, (int)F.size());
                        for (int i = 0; i < L && !found; ++i) {
                            for (int j = i + 1; j < L; ++j) {
                                int x = F[i], y = F[j];
                                if (!adjBit[x].test(y)) { a = x; b = y; found = true; break; }
                            }
                        }
                    }
                }

                if (!found) continue;

                // Apply 1 -> 2 swap
                inSet[v] = 0;
                --curK;
                for (int x : g[v]) --conflict[x];

                inSet[a] = 1; ++curK;
                for (int x : g[a]) ++conflict[x];

                inSet[b] = 1; ++curK;
                for (int x : g[b]) ++conflict[x];

                // Augment to maximal
                augment_greedy();

                improved = true;
                break; // restart scanning
            }
            ++rounds;
            if (rounds > 50) break; // safeguard
        }
    };

    // Attempt improvement on best found set
    if (bestK < N && elapsed() < time_limit) {
        vector<char> candidate = bestSel;
        int K = bestK;
        two_for_one_improve(candidate, K, 1.00);
        if (K > bestK) {
            bestK = K;
            bestSel = move(candidate);
        }
    }

    // Final validation and minor fix in case of any accidental conflicts
    // (should not happen due to construction, but safe-guard)
    vector<char> validSel = bestSel;
    vector<char> mark(N, 0);
    for (int v = 0; v < N; ++v) if (validSel[v]) mark[v] = 1;
    for (int v = 0; v < N; ++v) if (validSel[v]) {
        for (int u : g[v]) {
            if (u > v && validSel[u]) {
                // Resolve by removing higher degree (heuristic)
                if (deg[v] > deg[u]) validSel[v] = 0;
                else validSel[u] = 0;
            }
        }
    }

    // Output
    for (int i = 0; i < N; ++i) {
        if (validSel[i]) {
            putchar_unlocked('1');
        } else {
            putchar_unlocked('0');
        }
        putchar_unlocked('\n');
    }
    return 0;
}