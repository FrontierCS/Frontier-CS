#include <bits/stdc++.h>
using namespace std;

static const int INF_INT = 1e9;

struct Candidate {
    vector<int> a, b;
    long long E;
    vector<int> t;
};

static inline long long simulate_and_error(const vector<int>& a, const vector<int>& b, const vector<int>& T, int N, int L, vector<int>& out_counts) {
    out_counts.assign(N, 0);
    int x = 0;
    out_counts[x] = 1; // week 1: employee 0
    for (int w = 2; w <= L; ++w) {
        int y = (out_counts[x] & 1) ? a[x] : b[x];
        x = y;
        out_counts[x] += 1;
    }
    long long E = 0;
    for (int i = 0; i < N; ++i) {
        E += llabs((long long)out_counts[i] - (long long)T[i]);
    }
    return E;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, L;
    if (!(cin >> N >> L)) {
        return 0;
    }
    vector<int> T(N);
    for (int i = 0; i < N; ++i) cin >> T[i];

    // Random engine
    unsigned long long seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    std::mt19937_64 rng(seed);

    // Prepare some useful structures
    vector<int> indices(N);
    iota(indices.begin(), indices.end(), 0);

    // Default best candidate: simple cycle a = i+1, b = i (or i+2), to ensure connectivity
    Candidate best;
    best.a.assign(N, 0);
    best.b.assign(N, 0);
    for (int i = 0; i < N; ++i) {
        best.a[i] = (i + 1) % N;
        best.b[i] = (i + 2) % N;
    }
    vector<int> ttmp;
    best.E = simulate_and_error(best.a, best.b, T, N, L, best.t);

    auto build_candidate = [&](double ratioC, bool randomRotate, int bAssignMode) -> Candidate {
        // ratioC in (1, 2], create groups where max <= ratioC * min (within positive groups). Zeros grouped separately.
        // Sort by T ascending
        vector<int> ord = indices;
        stable_sort(ord.begin(), ord.end(), [&](int i, int j) {
            if (T[i] != T[j]) return T[i] < T[j];
            return i < j;
        });

        vector<vector<int>> groups;
        int i = 0;
        // group zeros
        int start = 0;
        while (start < N && T[ord[start]] == 0) start++;
        if (start > 0) {
            vector<int> gz;
            for (int k = 0; k < start; ++k) gz.push_back(ord[k]);
            groups.push_back(move(gz));
        }
        // positive groups
        while (start < N) {
            int gstart = start;
            int minv = T[ord[gstart]];
            int gend = gstart + 1;
            while (gend < N && (long long)T[ord[gend]] <= (long long)floor(ratioC * (double)minv + 1e-9)) {
                gend++;
            }
            vector<int> g;
            for (int k = gstart; k < gend; ++k) g.push_back(ord[k]);
            groups.push_back(move(g));
            start = gend;
        }

        // Build a-edges: within each group, create a cycle
        vector<int> a(N, 0), b(N, -1);
        for (auto &g : groups) {
            if (g.empty()) continue;
            int sz = (int)g.size();
            if (randomRotate && sz >= 2) {
                // random rotate within group to vary predecessors
                int shift = (int)(rng() % sz);
                if (shift) {
                    rotate(g.begin(), g.begin() + shift, g.end());
                }
                // also maybe small random swaps
                int swaps = min(sz, 3);
                for (int s = 0; s < swaps; ++s) {
                    int x = (int)(rng() % sz);
                    int y = (int)(rng() % sz);
                    if (x != y) swap(g[x], g[y]);
                }
            }
            for (int k = 0; k < sz; ++k) {
                int u = g[k];
                int v = g[(k + 1) % sz];
                a[u] = v;
            }
        }

        // Compute residual demands R_j = 2*T_j - sum_a_incoming_weights(j)
        vector<long long> Rin(N, 0);
        vector<int> predecessor(N, -1);
        // For each group, predecessor inside cycle:
        for (auto &g : groups) {
            int sz = (int)g.size();
            if (sz == 0) continue;
            for (int k = 0; k < sz; ++k) {
                int u = g[k];
                int v = g[(k + 1) % sz];
                // edge u -> v in 'a'
                predecessor[v] = u;
            }
        }
        for (int j = 0; j < N; ++j) {
            long long base = 0;
            if (predecessor[j] != -1) base = T[predecessor[j]];
            Rin[j] = 2LL * (long long)T[j] - base;
            // Rin can be small or zero; if negative due to randomRotate? Shouldn't happen for these groups by construction, except possibly zeros with random rotation within group of zeros (base 0 => fine).
            // But just in case, clamp at zero initial; we will allow overshoot later if necessary.
            if (Rin[j] < 0) Rin[j] = 0;
        }

        // Prepare multiset for residuals
        struct Node { long long r; int j; };
        struct Cmp {
            bool operator()(const Node& a, const Node& b) const {
                if (a.r != b.r) return a.r < b.r;
                return a.j < b.j;
            }
        };
        std::multiset<Node, Cmp> ms;
        vector<multiset<Node, Cmp>::iterator> itR(N);
        for (int j = 0; j < N; ++j) {
            itR[j] = ms.insert(Node{Rin[j], j});
        }

        vector<int> tokens; tokens.reserve(N);
        for (int u = 0; u < N; ++u) tokens.push_back(u);
        vector<char> used(N, 0);

        // Bridging across groups to ensure strong connectivity across groups
        int G = (int)groups.size();
        if (G > 1) {
            for (int gi = 0; gi < G; ++gi) {
                auto &gsrc = groups[gi];
                auto &gdst = groups[(gi + 1) % G];

                // Choose source token with minimal T to avoid overshoot
                int src = -1;
                int minT = INF_INT;
                for (int u : gsrc) {
                    if (!used[u] && T[u] < minT) {
                        minT = T[u];
                        src = u;
                    }
                }
                if (src == -1) {
                    // all used? pick any from gsrc
                    for (int u : gsrc) {
                        if (!used[u]) { src = u; break; }
                    }
                    if (src == -1) {
                        // fallback: any unused
                        for (int u = 0; u < N; ++u) if (!used[u]) { src = u; break; }
                    }
                }
                if (src == -1) continue; // should not happen

                // Choose destination j in gdst with maximum Rin and Rin >= T[src] if possible
                int dst = -1;
                long long bestR = -1;
                for (int v : gdst) {
                    if (Rin[v] > bestR) {
                        bestR = Rin[v];
                        dst = v;
                    }
                }
                if (dst == -1) {
                    dst = gdst[0];
                }
                // If bestR < T[src], try to find any with Rin >= T[src]
                if ((long long)T[src] > Rin[dst]) {
                    // scan others
                    int found = -1;
                    for (int v : gdst) {
                        if (Rin[v] >= (long long)T[src]) { found = v; break; }
                    }
                    if (found != -1) dst = found;
                }

                b[src] = dst;
                used[src] = 1;
                // Update residual
                ms.erase(itR[dst]);
                Rin[dst] -= (long long)T[src];
                itR[dst] = ms.insert(Node{Rin[dst], dst});
            }
        }

        // Prepare remaining tokens list
        vector<pair<int,int>> rem; rem.reserve(N);
        for (int u = 0; u < N; ++u) if (!used[u]) rem.emplace_back(T[u], u);

        // Assignment modes:
        // 0: best-fit decreasing by weight
        // 1: greedy to max residual
        if (bAssignMode == 0) {
            // sort descending by weight, random tie-break
            stable_sort(rem.begin(), rem.end(), [&](const pair<int,int>& A, const pair<int,int>& B){
                if (A.first != B.first) return A.first > B.first;
                return A.second < B.second;
            });
            for (auto &p : rem) {
                int w = p.first, u = p.second;
                // find smallest residual >= w
                Node key{(long long)w, -1};
                auto it = ms.lower_bound(key);
                int dst;
                if (it == ms.end()) {
                    // pick the largest residual
                    auto it2 = prev(ms.end());
                    dst = it2->j;
                } else {
                    dst = it->j;
                }
                b[u] = dst;
                // update
                ms.erase(itR[dst]);
                Rin[dst] -= (long long)w;
                itR[dst] = ms.insert(Node{Rin[dst], dst});
            }
        } else {
            // Random order or ascending, assign to max residual each time
            shuffle(rem.begin(), rem.end(), rng);
            for (auto &p : rem) {
                int w = p.first, u = p.second;
                // pick max residual
                auto it2 = prev(ms.end());
                int dst = it2->j;
                b[u] = dst;
                ms.erase(itR[dst]);
                Rin[dst] -= (long long)w;
                itR[dst] = ms.insert(Node{Rin[dst], dst});
            }
        }

        // Fill any unset b with a fallback (should not happen much)
        for (int u = 0; u < N; ++u) if (b[u] < 0) b[u] = a[u];

        Candidate cand;
        cand.a = move(a);
        cand.b = move(b);
        cand.E = simulate_and_error(cand.a, cand.b, T, N, L, cand.t);
        return cand;
    };

    // Try multiple candidates within time limit
    auto time_start = chrono::high_resolution_clock::now();
    const double TL = 1.9; // seconds
    int iterations = 0;

    vector<double> cList = {2.0, 1.8, 1.6, 1.4};
    while (true) {
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - time_start).count();
        if (elapsed > TL) break;

        for (double cval : cList) {
            // Mode 0 best-fit; Mode 1 greedy
            for (int mode = 0; mode < 2; ++mode) {
                bool randRotate = ((rng() >> 8) & 1);
                Candidate cand = build_candidate(cval, randRotate, mode);
                if (cand.E < best.E) {
                    best = move(cand);
                }
                iterations++;
                now = chrono::high_resolution_clock::now();
                elapsed = chrono::duration<double>(now - time_start).count();
                if (elapsed > TL) break;
            }
            auto now2 = chrono::high_resolution_clock::now();
            if (chrono::duration<double>(now2 - time_start).count() > TL) break;
        }
    }

    // Output best
    for (int i = 0; i < N; ++i) {
        cout << best.a[i] << " " << best.b[i] << "\n";
    }

    return 0;
}