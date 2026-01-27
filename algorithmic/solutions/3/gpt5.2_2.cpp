#include <bits/stdc++.h>
using namespace std;

static int SUBTASK, N;

static vector<int> ask(const vector<int>& ops) {
    cout << ops.size();
    for (int x : ops) cout << ' ' << x;
    cout << '\n';
    cout.flush();

    vector<int> res(ops.size());
    for (size_t i = 0; i < ops.size(); i++) {
        if (!(cin >> res[i])) exit(0);
        if (res[i] == -1) exit(0);
    }
    return res;
}

static void clear_set(const vector<int>& on) {
    if (on.empty()) return;
    (void)ask(on);
}

// Greedy maximal independent set on given vertex order; leaves the set lit at the end.
static vector<int> build_maximal_independent(const vector<int>& order, vector<char>& inSet) {
    vector<int> picked;
    picked.reserve(order.size());
    for (int v : order) {
        auto res = ask(vector<int>{v});
        if (res[0] == 0) {
            inSet[v] = 1;
            picked.push_back(v);
        } else {
            (void)ask(vector<int>{v}); // revert
        }
    }
    return picked;
}

// Given independent anchors A and vertices V, find for each v in V all neighbors in A (up to 2).
// Assumes S is empty on entry, and leaves S empty on exit.
static void find_neighbors_up_to2(const vector<int>& anchors,
                                 const vector<int>& vertices,
                                 vector<vector<int>>& neighOut) {
    int m = (int)anchors.size();
    if (vertices.empty()) return;
    if (m == 0) return;
    if (m == 1) {
        int a = anchors[0];
        for (int v : vertices) neighOut[v].push_back(a);
        return;
    }

    struct Node {
        int l, r;
        vector<int> vs;
        int mid = 0;
        int leftIdx = -1, rightIdx = -1;
        bool split = false;
    };

    vector<Node> cur;
    cur.push_back(Node{0, m, vertices});

    while (true) {
        bool anySplit = false;

        vector<Node> next;
        next.reserve(cur.size() * 2);

        // Prepare next nodes and record child indices.
        for (auto &nd : cur) {
            nd.split = false;
            nd.leftIdx = nd.rightIdx = -1;
            if (nd.r - nd.l <= 1) {
                nd.split = false;
                nd.leftIdx = (int)next.size();
                next.push_back(Node{nd.l, nd.r, nd.vs});
            } else {
                anySplit = true;
                nd.split = true;
                nd.mid = (nd.l + nd.r) >> 1;
                nd.leftIdx = (int)next.size();
                next.push_back(Node{nd.l, nd.mid, {}});
                nd.rightIdx = (int)next.size();
                next.push_back(Node{nd.mid, nd.r, {}});
            }
        }

        if (!anySplit) {
            // All leaves. Collect results.
            for (const auto &nd : cur) {
                // nd.l == nd.r-1
                int a = anchors[nd.l];
                for (int v : nd.vs) neighOut[v].push_back(a);
            }
            return;
        }

        // Build one big query for this level: for each split node, test left and right halves.
        vector<int> ops;
        // Conservative reserve: anchors toggles (4m) + vertex toggles (~8*|V|)
        ops.reserve((size_t)4 * (size_t)m + (size_t)8 * (size_t)vertices.size() + 100);

        for (const auto &nd : cur) {
            if (!nd.split) continue;
            int l = nd.l, mid = nd.mid, r = nd.r;

            // Left half test
            for (int i = l; i < mid; i++) ops.push_back(anchors[i]); // on
            for (int v : nd.vs) {
                ops.push_back(v); // on
                ops.push_back(v); // off
            }
            for (int i = l; i < mid; i++) ops.push_back(anchors[i]); // off

            // Right half test
            for (int i = mid; i < r; i++) ops.push_back(anchors[i]); // on
            for (int v : nd.vs) {
                ops.push_back(v); // on
                ops.push_back(v); // off
            }
            for (int i = mid; i < r; i++) ops.push_back(anchors[i]); // off
        }

        auto res = ask(ops);
        size_t pos = 0;

        // Parse and distribute vertices into next.
        for (const auto &nd : cur) {
            if (!nd.split) continue;
            int l = nd.l, mid = nd.mid, r = nd.r;

            // Left half: skip anchor on outputs
            pos += (size_t)(mid - l);
            // For each v: read bit on first toggle, skip second toggle
            for (int v : nd.vs) {
                int bit = res[pos];
                pos += 2;
                if (bit) next[nd.leftIdx].vs.push_back(v);
            }
            // skip anchor off outputs
            pos += (size_t)(mid - l);

            // Right half
            pos += (size_t)(r - mid);
            for (int v : nd.vs) {
                int bit = res[pos];
                pos += 2;
                if (bit) next[nd.rightIdx].vs.push_back(v);
            }
            pos += (size_t)(r - mid);
        }

        cur.swap(next);
        // S should be empty after the batch; our construction toggles everything off.
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> SUBTASK >> N)) return 0;

    if (N == 1) {
        cout << -1 << " 1\n";
        cout.flush();
        return 0;
    }
    if (N == 2) {
        // Any order is fine
        cout << -1 << " 1 2\n";
        cout.flush();
        return 0;
    }

    // Build maximal independent set I
    vector<int> order(N);
    iota(order.begin(), order.end(), 1);
    // Optional shuffle for better typical size; deterministic seed.
    {
        uint64_t seed = 1469598103934665603ULL;
        seed ^= (uint64_t)N + 0x9e3779b97f4a7c15ULL + (seed << 6) + (seed >> 2);
        seed ^= (uint64_t)SUBTASK + 0x9e3779b97f4a7c15ULL + (seed << 6) + (seed >> 2);
        mt19937 rng((uint32_t)(seed ^ (seed >> 32)));
        shuffle(order.begin(), order.end(), rng);
    }

    vector<char> inI(N + 1, 0);
    vector<int> I = build_maximal_independent(order, inI);
    clear_set(I); // ensure S is empty

    // Outside vertices
    vector<int> R;
    R.reserve(N - (int)I.size());
    for (int v = 1; v <= N; v++) if (!inI[v]) R.push_back(v);

    // Find for each outside vertex its neighbors in I (size 1 or 2)
    vector<vector<int>> neighI(N + 1);
    find_neighbors_up_to2(I, R, neighI);

    // Separate R1 (one anchor neighbor) and R2 (two anchor neighbors)
    vector<int> R1;
    R1.reserve(R.size());
    for (int v : R) {
        if ((int)neighI[v].size() == 1) R1.push_back(v);
        // size==2 -> singleton, no outside neighbor
    }

    // Build edges
    vector<vector<int>> adj(N + 1);
    adj.reserve(N + 1);

    auto add_edge = [&](int a, int b) {
        adj[a].push_back(b);
        adj[b].push_back(a);
    };

    for (int v : R) {
        for (int u : neighI[v]) add_edge(v, u);
    }

    // If there are R1 vertices, find their matching (outside-outside edges)
    if (!R1.empty()) {
        // Build maximal independent set J in matching graph induced by R1
        vector<char> inJ(N + 1, 0);
        vector<int> J = build_maximal_independent(R1, inJ);
        clear_set(J); // empty

        vector<int> W;
        W.reserve(R1.size() - J.size());
        for (int v : R1) if (!inJ[v]) W.push_back(v);

        // Find each w's unique neighbor in J
        vector<vector<int>> neighJ(N + 1);
        find_neighbors_up_to2(J, W, neighJ);

        for (int w : W) {
            if (neighJ[w].empty()) exit(0);
            int partner = neighJ[w][0];
            add_edge(w, partner);
        }
    }

    // Build a cycle traversal order
    // Ensure degrees are usable; for robustness, pick a start with nonempty adjacency.
    int start = 1;
    while (start <= N && adj[start].empty()) start++;
    if (start > N) exit(0);

    vector<int> perm;
    perm.reserve(N);

    int prev = 0, cur = start;
    for (int i = 0; i < N; i++) {
        perm.push_back(cur);
        if ((int)adj[cur].size() == 0) exit(0);
        int nxt;
        if ((int)adj[cur].size() == 1) {
            nxt = adj[cur][0];
        } else {
            int a = adj[cur][0], b = adj[cur][1];
            nxt = (a == prev ? b : a);
        }
        prev = cur;
        cur = nxt;
    }

    cout << -1;
    for (int x : perm) cout << ' ' << x;
    cout << '\n';
    cout.flush();
    return 0;
}