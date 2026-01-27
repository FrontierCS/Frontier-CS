#include <bits/stdc++.h>
using namespace std;

using ull = unsigned long long;

struct Timer {
    chrono::steady_clock::time_point start;
    Timer() { start = chrono::steady_clock::now(); }
    double elapsed_ms() const {
        return chrono::duration<double, milli>(chrono::steady_clock::now() - start).count();
    }
};

struct MISolver {
    int N;
    vector<vector<int>> g;
    vector<vector<ull>> adj_bits;
    int blocks;
    ull last_mask;

    mt19937 rng;

    MISolver(int n, vector<vector<ull>> &&adj) : N(n), adj_bits(move(adj)) {
        blocks = (N + 63) >> 6;
        int rem = N & 63;
        last_mask = rem ? ((1ULL << rem) - 1ULL) : ~0ULL;

        // Build adjacency lists from bitsets
        g.assign(N, {});
        for (int u = 0; u < N; ++u) {
            g[u].reserve(64); // rough
            for (int b = 0; b < blocks; ++b) {
                ull w = adj_bits[u][b];
                while (w) {
                    int t = __builtin_ctzll(w);
                    int v = (b << 6) + t;
                    if (v < N && v != u) g[u].push_back(v);
                    w &= w - 1;
                }
            }
        }
        rng.seed(chrono::high_resolution_clock::now().time_since_epoch().count());
    }

    vector<char> greedy_bucket_random() {
        vector<int> deg(N), pos(N);
        vector<char> active(N, 1), selected(N, 0);
        vector<vector<int>> buckets(N + 1);
        int activeCount = N;

        for (int i = 0; i < N; ++i) {
            deg[i] = (int)g[i].size();
            pos[i] = (int)buckets[deg[i]].size();
            buckets[deg[i]].push_back(i);
        }

        auto remove_vertex = [&](int x) {
            if (!active[x]) return;
            active[x] = 0;
            int dx = deg[x];
            auto &bx = buckets[dx];
            int ix = pos[x];
            int y = bx.back();
            bx[ix] = y;
            pos[y] = ix;
            bx.pop_back();
            --activeCount;

            for (int nb : g[x]) if (active[nb]) {
                int d = deg[nb];
                auto &from = buckets[d];
                int inb = pos[nb];
                int last = from.back();
                from[inb] = last;
                pos[last] = inb;
                from.pop_back();

                deg[nb] = d - 1;
                auto &to = buckets[d - 1];
                pos[nb] = (int)to.size();
                to.push_back(nb);
            }
        };

        while (activeCount > 0) {
            int mindeg = 0;
            while (mindeg <= N && buckets[mindeg].empty()) ++mindeg;
            if (mindeg > N) break;
            auto &b = buckets[mindeg];
            int idx = uniform_int_distribution<int>(0, (int)b.size() - 1)(rng);
            int v = b[idx];

            if (!active[v]) continue; // safety

            selected[v] = 1;
            remove_vertex(v);
            for (int u : g[v]) if (active[u]) remove_vertex(u);
        }
        return selected;
    }

    void improve_1for2(vector<char>& selected, double time_limit_ms, const Timer& timer) {
        // Build selected bitset and cover_count for non-selected
        vector<ull> Bsel(blocks, 0);
        vector<int> cover(N, 0);

        for (int i = 0; i < N; ++i) {
            if (selected[i]) {
                Bsel[i >> 6] |= (1ULL << (i & 63));
            }
        }
        for (int u = 0; u < N; ++u) if (selected[u]) {
            for (int v : g[u]) if (!selected[v]) cover[v]++;
        }

        auto recompute_cover_for = [&](int v) {
            int c = 0;
            for (int b = 0; b < blocks; ++b) {
                ull x = adj_bits[v][b] & Bsel[b];
                c += __builtin_popcountll(x);
            }
            cover[v] = c;
        };

        auto set_bit = [&](vector<ull>& bits, int i) {
            bits[i >> 6] |= (1ULL << (i & 63));
        };
        auto clear_bit = [&](vector<ull>& bits, int i) {
            bits[i >> 6] &= ~(1ULL << (i & 63));
        };

        bool improved = true;
        int rounds = 0;
        while (improved && timer.elapsed_ms() < time_limit_ms) {
            improved = false;
            vector<int> Slist;
            Slist.reserve(N);
            for (int i = 0; i < N; ++i) if (selected[i]) Slist.push_back(i);
            shuffle(Slist.begin(), Slist.end(), rng);

            for (int u : Slist) {
                if (timer.elapsed_ms() >= time_limit_ms) return;
                if (!selected[u]) continue;

                vector<int> Wnodes;
                Wnodes.reserve(g[u].size());
                for (int v : g[u]) {
                    if (!selected[v] && cover[v] == 1) Wnodes.push_back(v);
                }
                if ((int)Wnodes.size() < 2) continue;

                vector<ull> Wbits(blocks, 0);
                for (int v : Wnodes) set_bit(Wbits, v);

                int x = -1, y = -1;
                for (int a : Wnodes) {
                    int blk_a = a >> 6;
                    for (int b = 0; b < blocks; ++b) {
                        ull cand = Wbits[b] & ~adj_bits[a][b];
                        if (b == blk_a) cand &= ~(1ULL << (a & 63));
                        if (b == blocks - 1) cand &= last_mask;
                        if (cand) {
                            int t = __builtin_ctzll(cand);
                            int bidx = (b << 6) + t;
                            if (bidx < N) { x = a; y = bidx; }
                            break;
                        }
                    }
                    if (x != -1) break;
                }
                if (x == -1) continue;

                // Perform 1-for-2 swap: remove u, add x and y
                selected[u] = 0;
                clear_bit(Bsel, u);
                for (int w : g[u]) if (!selected[w]) cover[w]--;

                // Add x
                selected[x] = 1;
                set_bit(Bsel, x);
                for (int w : g[x]) if (!selected[w]) cover[w]++;

                // Add y
                selected[y] = 1;
                set_bit(Bsel, y);
                for (int w : g[y]) if (!selected[w]) cover[w]++;

                // u becomes non-selected; recompute its cover to be safe
                recompute_cover_for(u);

                improved = true;
                if (timer.elapsed_ms() >= time_limit_ms) return;
            }
            rounds++;
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

    int blocks = (N + 63) >> 6;
    vector<vector<ull>> adj_bits(N, vector<ull>(blocks, 0));

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj_bits[u][v >> 6] |= (1ULL << (v & 63));
        adj_bits[v][u >> 6] |= (1ULL << (u & 63));
    }

    MISolver solver(N, move(adj_bits));
    Timer timer;
    const double TOTAL_MS = 1900.0;

    vector<char> best;
    int bestK = -1;

    // Greedy restarts phase
    double greedy_phase_ms = TOTAL_MS * 0.6;
    int iter = 0;
    while (timer.elapsed_ms() < greedy_phase_ms) {
        auto sel = solver.greedy_bucket_random();
        int K = 0;
        for (char c : sel) K += c;
        if (K > bestK) {
            bestK = K;
            best = move(sel);
        }
        iter++;
        if (iter > 200) break; // safety cap
    }

    // If no run due to extremely fast timer, run at least once
    if (bestK < 0) {
        best = solver.greedy_bucket_random();
        bestK = 0;
        for (char c : best) bestK += c;
    }

    // Improvement phase on the best solution
    double remain = TOTAL_MS - timer.elapsed_ms();
    if (remain > 50.0) {
        solver.improve_1for2(best, timer.elapsed_ms() + remain, timer);
        bestK = 0;
        for (char c : best) bestK += c;
    }

    // Output solution
    for (int i = 0; i < N; ++i) {
        cout << (best[i] ? 1 : 0) << '\n';
    }
    return 0;
}