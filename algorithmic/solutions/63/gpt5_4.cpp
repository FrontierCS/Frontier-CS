#include <bits/stdc++.h>
using namespace std;

struct XorShift64 {
    uint64_t x;
    XorShift64(uint64_t seed=88172645463393265ull) { x = seed; }
    inline uint64_t next() {
        uint64_t y = x;
        y ^= y << 7;
        y ^= y >> 9;
        return x = y;
    }
    inline uint64_t next64() { return next(); }
    inline uint32_t next32() { return (uint32_t)next(); }
    inline int nextInt(int n) { return (int)(next64() % (uint64_t)n); }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if(!(cin >> N >> M)) {
        return 0;
    }
    vector<int> U(M), V(M);
    vector<vector<int>> adj(N);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        U[i] = u;
        V[i] = v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Bitset dimensions
    const int W = (N + 63) >> 6;
    const size_t TOTW = (size_t)N * (size_t)W;

    // Candidate pairs bitset (row-major: row A, column B)
    vector<uint64_t> cand(TOTW, ~0ull);
    // Clear diagonal and bits beyond N in each row
    for (int i = 0; i < N; i++) {
        size_t base = (size_t)i * W;
        // Zero diagonal
        int j = i;
        cand[base + (j >> 6)] &= ~(1ull << (j & 63));
        // Zero bits beyond N in last word
        int rem = (W << 6) - N;
        if (rem > 0) {
            uint64_t mask = (N & 63) ? ((1ull << (N & 63)) - 1ull) : ~0ull;
            cand[base + W - 1] &= mask;
        }
    }

    auto popcount_vec = [&](const vector<uint64_t>& vec)->long long {
        long long s = 0;
        for (size_t i = 0; i < vec.size(); i++) s += __builtin_popcountll(vec[i]);
        return s;
    };

    auto cand_count = [&]()->long long {
        return popcount_vec(cand);
    };

    long long curCandCount = cand_count();
    if (curCandCount <= 0) {
        // Should not happen, but just in case
        cout << "1 0 1" << endl;
        cout.flush();
        return 0;
    }

    // Helper BFS to compute farthest node and parents
    auto bfs = [&](int src, vector<int>& dist, vector<int>& par)->int{
        dist.assign(N, -1);
        par.assign(N, -1);
        queue<int> q;
        q.push(src);
        dist[src] = 0;
        while(!q.empty()){
            int v = q.front(); q.pop();
            for(int to: adj[v]){
                if(dist[to] == -1){
                    dist[to] = dist[v] + 1;
                    par[to] = v;
                    q.push(to);
                }
            }
        }
        int far = src;
        for(int i=0;i<N;i++){
            if(dist[i] > dist[far]) far = i;
        }
        return far;
    };

    // Find approximate center
    vector<int> distA, parA, distB, parB;
    int s = bfs(0, distA, parA);
    int t = bfs(s, distA, parA);
    bfs(t, distB, parB);
    // reconstruct path from s to t using parA (parents from last BFS (from s))
    vector<int> path;
    {
        int cur = t;
        while(cur != -1){
            path.push_back(cur);
            cur = parA[cur];
        }
        // path from t to s
        // we want center
    }
    int center = path[path.size()/2];

    XorShift64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    vector<uint64_t> bestReach; bestReach.reserve(TOTW);
    vector<uint64_t> tmpReach; tmpReach.reserve(TOTW);
    vector<char> bestBits; bestBits.reserve(M);
    vector<char> tmpBits; tmpBits.reserve(M);

    auto compute_orientation_and_reach = [&](const vector<long long>& key,
                                             vector<uint64_t>& reach,
                                             vector<char>& edgebits,
                                             long long& onesInCand)->void {
        // Build out adjacency according to key: edge u->v if key[u] > key[v]
        vector<vector<int>> out(N);
        edgebits.assign(M, 0);
        for (int i = 0; i < M; i++) {
            int u = U[i], v = V[i];
            if (key[u] > key[v]) {
                out[u].push_back(v);
                edgebits[i] = 0; // from U to V (0)
            } else {
                out[v].push_back(u);
                edgebits[i] = 1; // from V to U (1)
            }
        }
        // order vertices by ascending key
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        stable_sort(order.begin(), order.end(), [&](int a, int b){
            if (key[a] != key[b]) return key[a] < key[b];
            return a < b;
        });

        reach.assign(TOTW, 0ull);
        onesInCand = 0;

        // Map from vertex to its position, but not necessary for DP
        // DP: process in ascending key; for each v, reach[v] = union reach[w] for w in out[v], plus bits for w
        for (int idx = 0; idx < N; idx++) {
            int v = order[idx];
            size_t baseV = (size_t)v * W;
            // Union reach[w]
            for (int w : out[v]) {
                size_t baseW = (size_t)w * W;
                // OR blocks
                for (int t = 0; t < W; t++) {
                    reach[baseV + t] |= reach[baseW + t];
                }
            }
            // Add direct neighbors bits
            for (int w : out[v]) {
                reach[baseV + (w >> 6)] |= (1ull << (w & 63));
            }
            // Count ones in intersection with candidate for this row
            size_t baseC = baseV;
            for (int t = 0; t < W; t++) {
                uint64_t inter = cand[baseC + t] & reach[baseV + t];
                onesInCand += __builtin_popcountll(inter);
            }
        }
    };

    auto build_key_bfs = [&](int root)->vector<long long>{
        vector<int> dist(N, -1);
        queue<int> q;
        q.push(root);
        dist[root] = 0;
        while(!q.empty()){
            int v = q.front(); q.pop();
            for(int to: adj[v]) if(dist[to] == -1){
                dist[to] = dist[v] + 1;
                q.push(to);
            }
        }
        // tie-breaker: random 32-bit
        vector<long long> key(N);
        for (int i = 0; i < N; i++) {
            uint64_t r = rng.next64();
            key[i] = ((long long)dist[i] << 32) ^ (long long)(r & 0xffffffffu);
        }
        return key;
    };

    auto build_key_random = [&]()->vector<long long>{
        vector<long long> key(N);
        for (int i = 0; i < N; i++) {
            key[i] = (long long)rng.next64();
        }
        return key;
    };

    int maxQueries = 600;
    int qcount = 0;

    while (curCandCount > 1 && qcount < maxQueries) {
        long long targetHalf = curCandCount / 2;
        long long bestDiff = (1LL<<62);
        long long bestOnes = 0;

        // Try two orientations: BFS from center and random permutation
        // Attempt 1: BFS from center
        {
            vector<long long> key = build_key_bfs(center);
            long long ones = 0;
            compute_orientation_and_reach(key, tmpReach, tmpBits, ones);
            long long diff = llabs(ones - targetHalf);
            if (diff < bestDiff) {
                bestDiff = diff;
                bestOnes = ones;
                bestReach.swap(tmpReach);
                bestBits = tmpBits;
            }
        }
        // Attempt 2: Random permutation orientation
        {
            vector<long long> key = build_key_random();
            long long ones = 0;
            compute_orientation_and_reach(key, tmpReach, tmpBits, ones);
            long long diff = llabs(ones - targetHalf);
            if (diff < bestDiff) {
                bestDiff = diff;
                bestOnes = ones;
                bestReach.swap(tmpReach);
                bestBits = tmpBits;
            }
        }

        // Ask query
        cout << 0;
        for (int i = 0; i < M; i++) {
            cout << ' ' << (int)bestBits[i];
        }
        cout << '\n';
        cout.flush();

        int x;
        if (!(cin >> x)) {
            // If interactor died, exit
            return 0;
        }
        // Update candidate
        if (x == 1) {
            // cand &= bestReach
            for (size_t i = 0; i < TOTW; i++) cand[i] &= bestReach[i];
        } else {
            // cand &= ~bestReach
            for (size_t i = 0; i < TOTW; i++) cand[i] &= ~bestReach[i];
        }
        curCandCount = cand_count();
        qcount++;
        if (curCandCount <= 0) break;
    }

    // Find any remaining pair
    int A = -1, B = -1;
    if (curCandCount >= 1) {
        for (int i = 0; i < N; i++) {
            size_t base = (size_t)i * W;
            for (int t = 0; t < W; t++) {
                uint64_t w = cand[base + t];
                if (w) {
                    int b = __builtin_ctzll(w);
                    int j = (t << 6) + b;
                    if (j < N) {
                        A = i; B = j;
                        break;
                    }
                }
            }
            if (A != -1) break;
        }
    }
    if (A == -1 || B == -1) {
        // Fallback guess if something went wrong
        A = 0;
        B = (N >= 2 ? 1 : 0);
    }

    cout << 1 << ' ' << A << ' ' << B << '\n';
    cout.flush();
    return 0;
}