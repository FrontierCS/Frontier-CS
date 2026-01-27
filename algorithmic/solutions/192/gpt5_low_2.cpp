#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    vector<int> best_lab(n, 0);
    long long best_cut = -1;

    vector<int> lab(n), deg(n), opp(n), gain(n);
    for (int i = 0; i < n; ++i) deg[i] = (int)adj[i].size();

    // RNG
    uint64_t seed = chrono::steady_clock::now().time_since_epoch().count() ^ (uint64_t)(uintptr_t)&seed;
    mt19937_64 rng(seed);
    uniform_int_distribution<int> bit01(0,1);

    auto compute_initial = [&](vector<int>& lab) {
        fill(opp.begin(), opp.end(), 0);
        long long cut = 0;
        for (int u = 0; u < n; ++u) {
            for (int v : adj[u]) if (v > u) {
                if (lab[u] != lab[v]) { cut++; opp[u]++; opp[v]++; }
            }
        }
        for (int i = 0; i < n; ++i) gain[i] = deg[i] - 2*opp[i];
        return cut;
    };

    struct Node { int g; int v; };
    auto greedy_improve = [&](long long &cut) {
        // max-heap by gain
        priority_queue<Node, vector<Node>, function<bool(const Node&, const Node&)>> pq(
            [](const Node& a, const Node& b){ return a.g < b.g; });
        for (int i = 0; i < n; ++i) if (gain[i] > 0) pq.push({gain[i], i});
        vector<char> inq(n, 0);
        while (!pq.empty()) {
            Node cur = pq.top(); pq.pop();
            int v = cur.v;
            if (cur.g != gain[v] || gain[v] <= 0) continue;
            // flip v
            cut += gain[v];
            int lv = lab[v];
            for (int u : adj[v]) {
                bool sameBefore = (lab[u] == lv);
                if (sameBefore) {
                    opp[u] += 1;
                } else {
                    opp[u] -= 1;
                }
                int newg = deg[u] - 2*opp[u];
                gain[u] = newg;
                if (newg > 0) pq.push({newg, u});
            }
            opp[v] = deg[v] - opp[v];
            lab[v] ^= 1;
            gain[v] = -gain[v];
            if (gain[v] > 0) pq.push({gain[v], v});
        }
    };

    auto now = [](){ return chrono::steady_clock::now(); };
    auto start = now();
    const double TIME_LIMIT_SEC = 0.95;
    auto time_left = [&](){
        chrono::duration<double> el = now() - start;
        return TIME_LIMIT_SEC - el.count();
    };

    int restarts = 0;
    // Try an initial heuristic: start with random, then greedy, multiple restarts until time up
    while (time_left() > 0.01) {
        // random initial labeling
        for (int i = 0; i < n; ++i) lab[i] = bit01(rng);
        long long cut = compute_initial(lab);
        greedy_improve(cut);
        if (cut > best_cut) {
            best_cut = cut;
            best_lab = lab;
        }
        // Diversification: small random perturbations then greedy again
        // Try a few perturbation iterations within remaining time
        int perturb_rounds = 3;
        for (int round = 0; round < perturb_rounds && time_left() > 0.005; ++round) {
            // Flip k random vertices
            int k = max(1, n / 50); // ~2% of vertices
            vector<int> idx(n);
            iota(idx.begin(), idx.end(), 0);
            shuffle(idx.begin(), idx.end(), rng);
            vector<int> flipped;
            flipped.reserve(k);
            for (int i = 0; i < k; ++i) {
                int v = idx[i];
                // Update structures for flip
                int lv = lab[v];
                for (int u : adj[v]) {
                    bool sameBefore = (lab[u] == lv);
                    if (sameBefore) opp[u] += 1;
                    else opp[u] -= 1;
                    gain[u] = deg[u] - 2*opp[u];
                }
                opp[v] = deg[v] - opp[v];
                lab[v] ^= 1;
                gain[v] = -gain[v];
                // Update cut
                cut += gain[v]; // note: gain[v] already negated; but we need previous gain before flip.
                // The above is incorrect since gain[v] updated. Fix by computing delta before updating.
            }
            // The above had an issue; we'll recompute properly by flipping with delta captured:
            // To avoid complexity, recompute from scratch after perturbation.
            // Recompute opp, gain, cut after perturbation
            cut = compute_initial(lab);
            greedy_improve(cut);
            if (cut > best_cut) {
                best_cut = cut;
                best_lab = lab;
            }
        }
        restarts++;
    }

    // Fallback in case something odd: ensure at least one solution
    if (best_cut < 0) {
        for (int i = 0; i < n; ++i) best_lab[i] = 0;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << best_lab[i];
    }
    cout << '\n';
    return 0;
}