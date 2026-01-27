#include <bits/stdc++.h>
using namespace std;

static inline long long computeCutAndCross(const vector<int>& s, const vector<pair<int,int>>& edges, vector<int>& cross) {
    int n = (int)s.size() - 1;
    fill(cross.begin(), cross.end(), 0);
    long long cut = 0;
    for (const auto& e : edges) {
        int u = e.first, v = e.second;
        if (s[u] != s[v]) {
            ++cross[u];
            ++cross[v];
            ++cut;
        }
    }
    return cut;
}

static int fm_pass(vector<int>& s, const vector<vector<int>>& adj, const vector<pair<int,int>>& edges, const vector<int>& deg, mt19937& rng, chrono::steady_clock::time_point deadline) {
    int n = (int)s.size() - 1;
    vector<int> cross(n + 1, 0);
    // We don't actually need the 'cut' value here for the algorithm; compute for cross and D
    computeCutAndCross(s, edges, cross);

    vector<int> D(n + 1);
    for (int i = 1; i <= n; ++i) D[i] = deg[i] - 2 * cross[i];

    vector<char> moved(n + 1, 0);
    vector<int> seq; seq.reserve(n);
    vector<int> gains; gains.reserve(n);

    int bestK = 0;
    int sumGain = 0;
    int bestGain = 0;

    for (int step = 0; step < n; ++step) {
        if ((step & 15) == 0 && chrono::steady_clock::now() >= deadline) break;

        int bestV = -1;
        int bestDV = INT_MIN;

        for (int i = 1; i <= n; ++i) {
            if (!moved[i]) {
                int di = D[i];
                if (bestV == -1 || di > bestDV || (di == bestDV && (rng() & 1))) {
                    bestDV = di;
                    bestV = i;
                }
            }
        }
        if (bestV == -1) break;

        int v = bestV;
        int oldSide = s[v];
        int gain = D[v];

        s[v] ^= 1;
        moved[v] = 1;
        seq.push_back(v);
        gains.push_back(gain);

        sumGain += gain;
        if (sumGain > bestGain) {
            bestGain = sumGain;
            bestK = (int)seq.size();
        }

        for (int u : adj[v]) {
            if (moved[u]) continue;
            bool crossing_before = (s[u] != oldSide);
            if (crossing_before) D[u] += 2;
            else D[u] -= 2;
        }
    }

    // Revert flips beyond bestK to keep best state
    for (int j = (int)seq.size() - 1; j >= bestK; --j) {
        int v2 = seq[j];
        s[v2] ^= 1;
    }

    return bestGain;
}

static void local_search(vector<int>& s, long long& cut, const vector<vector<int>>& adj, const vector<pair<int,int>>& edges, const vector<int>& deg, mt19937& rng, chrono::steady_clock::time_point deadline) {
    while (chrono::steady_clock::now() < deadline) {
        int gain = fm_pass(s, adj, edges, deg, rng, deadline);
        if (gain <= 0) break;
    }
    vector<int> cross(s.size(), 0);
    cut = computeCutAndCross(s, edges, cross);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<vector<int>> adj(n + 1);
    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
    }

    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    vector<int> deg(n + 1);
    for (int i = 1; i <= n; ++i) deg[i] = (int)adj[i].size();

    random_device rd;
    mt19937 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ ((uint64_t)rd() << 1));

    auto start = chrono::steady_clock::now();
    // Adjust time limit as needed; choose 1800ms by default
    auto deadline = start + chrono::milliseconds(1800);

    // Initial solutions
    vector<int> bestS(n + 1, 0);
    long long bestCut = -1;

    // Init 1: random
    vector<int> s1(n + 1);
    for (int i = 1; i <= n; ++i) s1[i] = (rng() & 1);
    long long cut1 = 0;
    local_search(s1, cut1, adj, edges, deg, rng, deadline);
    if (cut1 > bestCut) { bestCut = cut1; bestS = s1; }

    if (chrono::steady_clock::now() < deadline) {
        // Init 2: greedy by random permutation
        vector<int> s2(n + 1, -1);
        vector<int> order(n);
        iota(order.begin(), order.end(), 1);
        shuffle(order.begin(), order.end(), rng);
        vector<int> assigned(n + 1, 0);
        for (int idx = 0; idx < n; ++idx) {
            int v = order[idx];
            int cnt0 = 0, cnt1 = 0;
            for (int u : adj[v]) {
                if (s2[u] == 0) ++cnt0;
                else if (s2[u] == 1) ++cnt1;
            }
            if (cnt0 > cnt1) s2[v] = 1;
            else if (cnt1 > cnt0) s2[v] = 0;
            else s2[v] = (rng() & 1);
            assigned[v] = 1;
        }
        long long cut2 = 0;
        local_search(s2, cut2, adj, edges, deg, rng, deadline);
        if (cut2 > bestCut) { bestCut = cut2; bestS = s2; }
    }

    // Iterated local search with perturbations
    while (chrono::steady_clock::now() < deadline) {
        vector<int> s = bestS;
        int kbase = max(1, n / 20); // ~5% perturbation
        int kvar = (n >= 50 ? (int)(rng() % max(1, n / 10)) : 0);
        int k = min(n, max(1, kbase + kvar / 2));

        // Apply random perturbation (flip k unique vertices)
        vector<int> idx(n);
        iota(idx.begin(), idx.end(), 1);
        shuffle(idx.begin(), idx.end(), rng);
        for (int i = 0; i < k; ++i) s[idx[i]] ^= 1;

        long long cut = 0;
        local_search(s, cut, adj, edges, deg, rng, deadline);
        if (cut > bestCut) { bestCut = cut; bestS = s; }
        // If time is nearly up, break
        if (chrono::steady_clock::now() + chrono::milliseconds(50) >= deadline) break;
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (bestS[i] & 1);
    }
    cout << '\n';

    return 0;
}