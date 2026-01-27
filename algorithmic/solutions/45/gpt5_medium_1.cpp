#include <bits/stdc++.h>
using namespace std;

#ifdef _WIN32
#define getchar_unlocked getchar
#endif

struct FastScanner {
    static inline int gc() { return getchar_unlocked(); }
    template<typename T>
    bool readInt(T &out) {
        int c = gc();
        if (c == EOF) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = gc();
            if (c == EOF) return false;
        }
        int neg = 0;
        if (c == '-') { neg = 1; c = gc(); }
        long long val = 0;
        while (c >= '0' && c <= '9') {
            val = val * 10 + (c - '0');
            c = gc();
        }
        out = (T)(neg ? -val : val);
        return true;
    }
    bool readDouble(double &out) {
        int c = gc();
        if (c == EOF) return false;
        while (c != '-' && c != '.' && (c < '0' || c > '9')) {
            c = gc();
            if (c == EOF) return false;
        }
        string s;
        while (c == '-' || c == '.' || (c >= '0' && c <= '9')) {
            s.push_back((char)c);
            c = gc();
        }
        out = stod(s);
        return true;
    }
} fs;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long m;
    int k;
    double eps;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);
    fs.readInt(k);
    fs.readDouble(eps);

    vector<vector<int>> adj(n);
    adj.shrink_to_fit(); // no-op but hints no pre-reserve

    for (long long i = 0; i < m; ++i) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        if (u == v) continue; // ignore self-loops to avoid bias
        --u; --v;
        if (u < 0 || v < 0 || u >= n || v >= n) continue; // safety
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Order vertices by degree (descending)
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);

    // Light randomization
    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    shuffle(order.begin(), order.end(), rng);

    vector<int> deg(n);
    for (int i = 0; i < n; ++i) deg[i] = (int)adj[i].size();

    sort(order.begin(), order.end(), [&](int a, int b){
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });

    int ideal = (n + k - 1) / k;
    int capacity = (int)floor((1.0 + eps) * (double)ideal + 1e-12);
    if (capacity < 1) capacity = 1;

    vector<int> part(n, -1);
    vector<int> partSize(k, 0);

    vector<int> cnt(k, 0), seen(k, 0);
    int curStamp = 1;
    vector<int> usedParts;
    usedParts.reserve(k);

    // LDG-like assignment
    for (int idx = 0; idx < n; ++idx) {
        int v = order[idx];
        usedParts.clear();
        ++curStamp;
        for (int u : adj[v]) {
            int pu = part[u];
            if (pu >= 0) {
                if (seen[pu] != curStamp) {
                    seen[pu] = curStamp;
                    cnt[pu] = 1;
                    usedParts.push_back(pu);
                } else {
                    cnt[pu]++;
                }
            }
        }

        int bestPart = -1;
        int bestCnt = -1;

        for (int p : usedParts) {
            if (partSize[p] >= capacity) continue;
            int c = cnt[p];
            if (c > bestCnt) {
                bestCnt = c;
                bestPart = p;
            } else if (c == bestCnt && bestPart != -1) {
                if (partSize[p] < partSize[bestPart]) bestPart = p;
            }
        }

        if (bestPart == -1 || bestCnt <= 0) {
            // Choose least loaded part
            int minLoad = INT_MAX, chosen = -1;
            for (int p = 0; p < k; ++p) {
                if (partSize[p] < capacity) {
                    if (partSize[p] < minLoad) {
                        minLoad = partSize[p];
                        chosen = p;
                    }
                }
            }
            if (chosen == -1) {
                // Shouldn't happen if total capacity >= n, but fallback
                chosen = (int)(rng() % k);
            }
            bestPart = chosen;
        }
        part[v] = bestPart;
        partSize[bestPart]++;
    }

    // Simple refinement to reduce edge cut
    auto t0 = chrono::steady_clock::now();
    const double timeLimitSec = 0.95; // soft limit
    int maxPasses = 2;
    for (int pass = 0; pass < maxPasses; ++pass) {
        bool improved = false;
        vector<int> allVertices(n);
        iota(allVertices.begin(), allVertices.end(), 0);
        shuffle(allVertices.begin(), allVertices.end(), rng);

        for (int v : allVertices) {
            // Time guard
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - t0).count();
            if (elapsed > timeLimitSec) break;

            int A = part[v];
            usedParts.clear();
            ++curStamp;

            for (int u : adj[v]) {
                int pu = part[u];
                if (seen[pu] != curStamp) {
                    seen[pu] = curStamp;
                    cnt[pu] = 1;
                    usedParts.push_back(pu);
                } else {
                    cnt[pu]++;
                }
            }
            int degA = (seen[A] == curStamp) ? cnt[A] : 0;

            int bestB = A;
            int bestGain = 0;
            for (int B : usedParts) {
                if (B == A) continue;
                if (partSize[B] >= capacity) continue;
                int gain = cnt[B] - degA; // improvement in reducing EC if positive
                if (gain > bestGain || (gain == bestGain && bestB == A && partSize[B] < partSize[bestB])) {
                    bestGain = gain;
                    bestB = B;
                }
            }

            if (bestB != A && bestGain > 0) {
                part[v] = bestB;
                partSize[bestB]++;
                partSize[A]--;
                improved = true;
            }
        }
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - t0).count();
        if (!improved || elapsed > timeLimitSec) break;
    }

    // Output
    // Ensure 1..k labels
    for (int i = 0; i < n; ++i) {
        int lbl = part[i] + 1;
        if (lbl < 1) lbl = 1;
        if (lbl > k) lbl = k;
        cout << lbl << (i + 1 == n ? '\n' : ' ');
    }
    return 0;
}