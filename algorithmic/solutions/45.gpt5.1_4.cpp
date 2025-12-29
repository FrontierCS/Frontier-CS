#include <bits/stdc++.h>
using namespace std;

static uint64_t rng_state = 123456789123456789ULL;
inline uint32_t fastRand() {
    rng_state ^= rng_state << 7;
    rng_state ^= rng_state >> 9;
    rng_state ^= rng_state << 8;
    return (uint32_t)rng_state;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    long long m;
    double eps;
    if (scanf("%d %lld %d %lf", &n, &m, &k, &eps) != 4) {
        return 0;
    }

    // Adjacency list using edge arrays
    int maxEdges = (int)(2 * m + 5); // some slack
    vector<int> head(n + 1, -1);
    vector<int> to(maxEdges);
    vector<int> nextEdge(maxEdges);
    int edgeCnt = 0;

    for (long long i = 0; i < m; ++i) {
        int u, v;
        if (scanf("%d %d", &u, &v) != 2) return 0;
        if (u == v) continue; // skip self-loops
        if (u < 1 || u > n || v < 1 || v > n) continue;

        if (edgeCnt + 2 > maxEdges) continue; // safety; should not happen in valid tests

        to[edgeCnt] = v;
        nextEdge[edgeCnt] = head[u];
        head[u] = edgeCnt++;
        to[edgeCnt] = u;
        nextEdge[edgeCnt] = head[v];
        head[v] = edgeCnt++;
    }

    long long ideal_ll = ((long long)n + k - 1) / k; // ceil(n/k)
    int ideal = (int)ideal_ll;
    int cap = (int)floor((1.0 + eps) * ideal + 1e-9);

    vector<int> part(n + 1, 0);
    vector<int> partSize(k + 1, 0);
    vector<char> visited(n + 1, 0);

    // BFS-based initial partitioning
    queue<int> q;
    int curPart = 1;
    int assignedInCur = 0;
    for (int start = 1; start <= n; ++start) {
        if (visited[start]) continue;
        visited[start] = 1;
        q.push(start);
        while (!q.empty()) {
            int v = q.front(); q.pop();
            if (curPart > k) curPart = k;
            part[v] = curPart;
            partSize[curPart]++;
            assignedInCur++;
            if (assignedInCur >= ideal && curPart < k) {
                curPart++;
                assignedInCur = 0;
            }
            for (int e = head[v]; e != -1; e = nextEdge[e]) {
                int u = to[e];
                if (!visited[u]) {
                    visited[u] = 1;
                    q.push(u);
                }
            }
        }
    }

    // Ensure initial partition obeys cap (it should)
    // Refinement via balanced label propagation
    vector<int> perm(n);
    for (int i = 0; i < n; ++i) perm[i] = i + 1;
    vector<int> cnt(k + 1, 0);
    vector<int> usedParts;
    usedParts.reserve(64);

    const int MAX_PASSES = 10;
    clock_t t0 = clock();

    int pass = 0;
    while (pass < MAX_PASSES) {
        double elapsed = double(clock() - t0) / CLOCKS_PER_SEC;
        if (elapsed > 0.9) break;

        // Fisher-Yates shuffle using fastRand
        for (int i = n - 1; i > 0; --i) {
            int j = fastRand() % (i + 1);
            int tmp = perm[i];
            perm[i] = perm[j];
            perm[j] = tmp;
        }

        int changed = 0;

        for (int idx = 0; idx < n; ++idx) {
            int v = perm[idx];
            int cur = part[v];
            int headV = head[v];
            if (headV == -1) continue; // isolated

            usedParts.clear();

            // Count neighbors by part
            for (int e = headV; e != -1; e = nextEdge[e]) {
                int u = to[e];
                int p = part[u];
                if (cnt[p] == 0) usedParts.push_back(p);
                cnt[p]++;
            }

            int oldCount = cnt[cur]; // neighbors in current part
            int bestPart = cur;
            int bestCount = oldCount;

            // Evaluate moves to neighboring parts
            for (int p : usedParts) {
                if (p == cur) continue;
                if (partSize[p] + 1 > cap) continue;
                int c = cnt[p];
                if (c > bestCount || (c == bestCount && (fastRand() & 1))) {
                    bestPart = p;
                    bestCount = c;
                }
            }

            if (bestPart != cur && bestCount > oldCount && partSize[bestPart] + 1 <= cap) {
                partSize[cur]--;
                partSize[bestPart]++;
                part[v] = bestPart;
                changed++;
            }

            // Reset counts
            for (int p : usedParts) cnt[p] = 0;
        }

        pass++;
        if (changed == 0) break;
    }

    // Output partition
    for (int i = 1; i <= n; ++i) {
        printf("%d%c", part[i], (i == n ? '\n' : ' '));
    }

    return 0;
}